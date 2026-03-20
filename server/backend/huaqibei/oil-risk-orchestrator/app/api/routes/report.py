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
from fastapi.responses import JSONResponse

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
    raise BusinessError(
        code=BusinessErrorCode.NOT_IMPLEMENTED,
        message="PDF 导出暂未实现",
        status_code=501,
        details={"resource": "report_pdf", "id": report_id},
    )
