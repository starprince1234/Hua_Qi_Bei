"""E2E contract test for Oil Risk Orchestrator (OpenAPI aligned)."""

from __future__ import annotations

import json
import os
from typing import Any

# IMPORTANT: env vars must be set before importing app.main.
os.environ.setdefault("USE_MOCK_MODEL", "true")

from fastapi.testclient import TestClient

from app.main import app


def build_csv_rows(count: int = 30, base: float = 70.0) -> str:
    rows = ["date,open,high,low,close,volume"]
    for i in range(count):
        day = i + 1
        value = base + (i * 0.1)
        rows.append(
            f"2026-01-{day:02d},{value:.1f},{value + 1:.1f},{value - 1:.1f},{value + 0.5:.1f},{1000000 + i}"
        )
    return "\n".join(rows)


def json_body(resp) -> dict[str, Any]:
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise AssertionError(f"Expected JSON response, got content-type={content_type}")
    return resp.json()


def assert_success_envelope(resp, expected_status: int = 200) -> dict[str, Any]:
    assert resp.status_code == expected_status, f"Unexpected status: {resp.status_code}"
    body = json_body(resp)
    assert body.get("success") is True, f"Expected success=true, got {body}"
    assert body.get("code") == 200, f"Expected code=200, got {body}"
    return body


def run() -> None:
    client = TestClient(app, raise_server_exceptions=False)

    # 1) health
    health = client.get("/api/v1/health")
    health_body = assert_success_envelope(health, 200)
    assert health_body.get("data", {}).get("status") == "ok"

    # 2) upload (strict_mode explicitly passed as bool-like string, backend does explicit parse)
    upload = client.post(
        "/api/v1/upload",
        files={"file": ("sample.csv", build_csv_rows(), "text/csv")},
        data={
            "dataset_type": "oil_price_factors",
            "timezone": "UTC",
            "frequency": "D",
            "strict_mode": "false",
            "encoding": "utf-8",
        },
    )
    upload_body = assert_success_envelope(upload, 200)
    file_id = upload_body.get("data", {}).get("file_id")
    assert file_id, "upload response missing file_id"

    # 3) predict
    predict_payload = {
        "file_id": file_id,
        "horizon": 5,
        "target": "log_return",
        "quantiles": [0.05, 0.5, 0.95],
        "industries": ["aviation", "shipping", "chemical"],
        "include_explainability": True,
        "include_knowledge_graph": True,
        "include_report": True,
        "report_style": "banking",
    }
    predict = client.post("/api/v1/predict", json=predict_payload)
    predict_body = assert_success_envelope(predict, 200)
    predict_data = predict_body.get("data", {})

    expected_blocks = {
        "prediction",
        "future_path",
        "shock_signal",
        "explainability",
        "knowledge_graph",
        "factor_selection_reasons",
        "report",
        "data_processing_log",
    }
    missing_blocks = sorted(expected_blocks - set(predict_data.keys()))
    assert not missing_blocks, f"predict response missing blocks: {missing_blocks}"

    report_id = predict_data.get("report", {}).get("report_id")
    assert report_id, "predict response missing report.report_id"

    # 4) report
    report = client.get(f"/api/v1/report/{report_id}")
    report_body = assert_success_envelope(report, 200)
    sections = report_body.get("data", {}).get("sections", {})
    for key in [
        "executive_summary",
        "trend_and_confidence",
        "key_drivers",
        "industry_impacts",
        "risks_and_limits",
    ]:
        assert key in sections, f"report.sections missing field: {key}"

    # 5) report pdf (contract: 200 pdf or 501 not implemented)
    report_pdf = client.get(f"/api/v1/report/{report_id}/pdf")
    if report_pdf.status_code == 200:
        content_type = report_pdf.headers.get("content-type", "")
        assert content_type.startswith("application/pdf"), (
            f"Expected application/pdf, got {content_type}"
        )
        assert report_pdf.content, "PDF response body is empty"
    elif report_pdf.status_code == 501:
        pdf_body = json_body(report_pdf)
        assert pdf_body.get("message") == "NOT_IMPLEMENTED", pdf_body
    else:
        raise AssertionError(f"Unexpected /report/{{id}}/pdf status: {report_pdf.status_code}")

    # 6) missing report -> 404 NOT_FOUND
    missing_report = client.get("/api/v1/report/not-exists")
    assert missing_report.status_code == 404, missing_report.text
    missing_body = json_body(missing_report)
    assert missing_body.get("message") == "NOT_FOUND", missing_body

    # 7) bad predict input (missing file_id/oil_data) -> 400/422 validation-style error
    bad_predict = client.post(
        "/api/v1/predict",
        json={"horizon": 5, "target": "log_return", "quantiles": [0.05, 0.5, 0.95]},
    )
    assert bad_predict.status_code in (400, 422), bad_predict.text
    bad_body = json_body(bad_predict)
    assert bad_body.get("message") in {"VALIDATION_ERROR", "MISSING_INPUT"}, bad_body

    details_text = json.dumps(bad_body.get("details", {}), ensure_ascii=False)
    assert "file_id" in details_text and "oil_data" in details_text, bad_body

    print("E2E contract test passed.")


if __name__ == "__main__":
    run()
