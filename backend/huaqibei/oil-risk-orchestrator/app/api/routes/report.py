"""
报告路由

职责：
    - 提供知识图谱路径查询端点
    - 提供因子字典查询端点
    - 供前端展示图谱与因子信息

禁止：
    - 在此文件中做预测计算
    - 在此文件中调用模型 API
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from datetime import datetime

from app.knowledge_graph.graph_query import GraphQuery
from app.explainability.factor_dictionary import FACTOR_METADATA
from app.schemas.report_schema import APIResponse
from app.services.factor_reason_service import FactorReasonService
from app.services.report_service import ReportService
from app.core.logger import get_logger
from app.core.errors import BusinessError, BusinessErrorCode

logger = get_logger(__name__)

router = APIRouter(prefix="/report", tags=["Report"])

_graph = GraphQuery()
_factor_reason_svc = FactorReasonService()
_report_svc = ReportService()
_industry_alias = {
    "refinery": "chemical",
    "logistics": "shipping",
    "heavy_manufacturing": "manufacturing",
}


def _sanitize_pdf_text(text: str) -> str:
    """Keep ASCII-safe content for built-in PDF text stream."""
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return safe.encode("ascii", errors="replace").decode("ascii")


def _wrap_text(text: str, max_chars: int = 90) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _build_simple_pdf(title: str, sections: list[tuple[str, str]]) -> bytes:
    """Build a minimal single-font PDF using built-in objects only."""
    lines: list[str] = [title, ""]
    for section_title, body in sections:
        lines.append(section_title)
        lines.extend(_wrap_text(body or ""))
        lines.append("")

    page_height = 842
    margin_top = 800
    line_height = 14
    max_lines_per_page = 52

    pages: list[list[str]] = []
    cursor: list[str] = []
    for line in lines:
        cursor.append(_sanitize_pdf_text(line))
        if len(cursor) >= max_lines_per_page:
            pages.append(cursor)
            cursor = []
    if cursor:
        pages.append(cursor)

    objects: list[str] = []
    objects.append("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")

    page_count = len(pages)
    kids_refs = " ".join([f"{3 + i * 2} 0 R" for i in range(page_count)])
    objects.append(f"2 0 obj << /Type /Pages /Kids [{kids_refs}] /Count {page_count} >> endobj\n")

    font_obj_id = 3 + page_count * 2

    for idx, page_lines in enumerate(pages):
        page_obj_id = 3 + idx * 2
        content_obj_id = page_obj_id + 1

        objects.append(
            f"{page_obj_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 {page_height}] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> /Contents {content_obj_id} 0 R >> endobj\n"
        )

        stream_lines = ["BT", f"/F1 11 Tf", f"50 {margin_top} Td"]
        first_line = True
        for line in page_lines:
            if first_line:
                stream_lines.append(f"({line}) Tj")
                first_line = False
            else:
                stream_lines.append(f"0 -{line_height} Td ({line}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines) + "\n"
        stream_bytes = stream.encode("ascii", errors="replace")
        objects.append(
            f"{content_obj_id} 0 obj << /Length {len(stream_bytes)} >> stream\n{stream}endstream\nendobj\n"
        )

    objects.append(f"{font_obj_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    pdf_header = b"%PDF-1.4\n"
    body = b""
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf_header) + len(body))
        body += obj.encode("ascii", errors="replace")

    xref_start = len(pdf_header) + len(body)
    xref = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n")

    trailer = (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    )

    return pdf_header + body + "".join(xref).encode("ascii") + trailer.encode("ascii")


@router.get(
    "/knowledge-graph/path/{industry}",
    summary="查询行业传导路径",
    response_model=APIResponse,
    responses={
        404: {"model": APIResponse},
        500: {"model": APIResponse},
    },
)
async def get_industry_path(industry: str) -> JSONResponse:
    """
    查询指定行业的油价传导路径（知识图谱节点链）。

    Args:
        industry: 行业标识符（aviation/shipping/chemical/energy/
                  agriculture/manufacturing/finance）。

    Returns:
        节点 ID 列表 + 中文标签列表。
    """
    mapped = _industry_alias.get(industry, industry)
    path_ids = _graph.get_path(mapped)

    if not path_ids:
        raise BusinessError(
            code=BusinessErrorCode.NOT_FOUND,
            message=f"未找到行业 {industry} 的传导路径",
            status_code=404,
        )

    path_labels = _graph.get_path_labels(mapped)

    return JSONResponse(
        content=APIResponse.ok(
            data={
                "industry": industry,
                "industry_mapped": mapped,
                "path_nodes": path_ids,
                "path_labels": path_labels,
                "arrow_path": " → ".join(path_labels),
            }
        ).model_dump()
    )


@router.get(
    "/factors",
    summary="获取全量因子字典",
    response_model=APIResponse,
    responses={500: {"model": APIResponse}},
)
async def get_factor_dictionary() -> JSONResponse:
    """
    返回系统支持的全量因子元数据字典。

    Returns:
        因子名 → 中文名、类别、定义、单位 字典。
    """
    factors = [
        {
            "factor_name": k,
            "name_cn": v["name_cn"],
            "category": v["category"].value,
            "definition": v["definition"],
            "unit": v["unit"],
        }
        for k, v in FACTOR_METADATA.items()
    ]

    return JSONResponse(
        content=APIResponse.ok(
            data={"total": len(factors), "factors": factors}
        ).model_dump()
    )


@router.get(
    "/factors/reasons",
    summary="获取统计筛选理由标签",
    response_model=APIResponse,
    responses={500: {"model": APIResponse}},
)
async def get_factor_reasons() -> JSONResponse:
    """返回保留/淘汰因子的统计筛选理由标签。"""
    payload = _factor_reason_svc.get_reason_catalog()
    return JSONResponse(content=APIResponse.ok(data=payload).model_dump())


@router.get(
    "/{report_id}",
    summary="按 report_id 获取结构化报告",
    response_model=APIResponse,
    responses={
        404: {"model": APIResponse},
        500: {"model": APIResponse},
    },
)
async def get_report(report_id: str) -> JSONResponse:
    report = _report_svc.get_report_result(report_id)
    if report is None:
        raise BusinessError(
            code=BusinessErrorCode.NOT_FOUND,
            message="报告不存在",
            status_code=404,
            details={"resource": "report", "id": report_id},
        )
    return JSONResponse(content=APIResponse.ok(data=report.model_dump()).model_dump())


@router.get(
    "/{report_id}/pdf",
    summary="下载报告 PDF（可选实现）",
    response_model=APIResponse,
    responses={
        404: {"model": APIResponse},
        501: {"model": APIResponse},
        500: {"model": APIResponse},
    },
)
async def download_report_pdf(report_id: str) -> JSONResponse:
    report = _report_svc.get_report(report_id)
    if report is None:
        raise BusinessError(
            code=BusinessErrorCode.NOT_FOUND,
            message="报告不存在",
            status_code=404,
            details={"resource": "report_pdf", "id": report_id},
        )

    sections = [
        ("Executive Summary", report.executive_summary or ""),
        ("Detailed Analysis", report.detailed_analysis or ""),
        ("Risk Advice", report.risk_advice or ""),
    ]
    pdf_bytes = _build_simple_pdf(
        title=f"Oil Risk Report - {report.report_id}",
        sections=sections,
    )

    filename = f"oil-risk-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
