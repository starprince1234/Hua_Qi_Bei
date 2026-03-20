"""
API 集成测试脚本

使用 httpx 对本地运行的 API 进行基础功能验证。
运行前请确保服务已启动：uvicorn app.main:app --host 0.0.0.0 --port 8000

使用方法：
    python test_api.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys
from datetime import date, timedelta
from typing import Any

try:
    import httpx
except ImportError:
    print("请先安装 httpx: pip install httpx")
    sys.exit(1)


BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


def _url(path: str) -> str:
    return f"{BASE_URL}{API_PREFIX}{path}"


def _print_result(name: str, resp: httpx.Response) -> None:
    status_icon = "✅" if resp.status_code < 300 else "❌"
    print(f"{status_icon} [{resp.status_code}] {name}")
    try:
        body = resp.json()
        print(json.dumps(body, ensure_ascii=False, indent=2)[:600])
    except Exception:
        print(resp.text[:300])
    print()


def _make_mock_data(n: int = 60) -> list[dict[str, Any]]:
    """生成 n 条 mock 油价数据。"""
    import random

    records = []
    price = 80.0
    today = date.today()
    for i in range(n):
        d = today - timedelta(days=n - i)
        change = random.gauss(0, 0.01)
        price = max(20.0, price * (1 + change))
        records.append(
            {
                "date": d.isoformat(),
                "open": round(price * 0.99, 2),
                "high": round(price * 1.01, 2),
                "low": round(price * 0.98, 2),
                "close": round(price, 2),
                "volume": random.randint(100000, 500000),
            }
        )
    return records


def test_health(client: httpx.Client) -> bool:
    resp = client.get(_url("/health"))
    _print_result("GET /health", resp)
    return resp.status_code == 200


def test_model_service_info(client: httpx.Client) -> bool:
    resp = client.get(_url("/model-service/info"))
    _print_result("GET /model-service/info", resp)
    return resp.status_code == 200


def test_predict_mock(client: httpx.Client) -> bool:
    payload = {
        "data": _make_mock_data(60),
        "forecast_horizon": 7,
        "include_shap": True,
        "mock_mode": True,
    }
    resp = client.post(_url("/predict"), json=payload, timeout=30)
    _print_result("POST /predict (mock_mode=True)", resp)
    return resp.status_code == 200


def test_report_mock(client: httpx.Client) -> bool:
    payload = {
        "data": _make_mock_data(60),
        "forecast_horizon": 7,
        "mock_mode": True,
        "report_format": "json",
    }
    resp = client.post(_url("/report"), json=payload, timeout=60)
    _print_result("POST /report (mock_mode=True)", resp)
    return resp.status_code == 200


def test_upload(client: httpx.Client) -> bool:
    import csv
    import io

    records = _make_mock_data(60)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["date", "open", "high", "low", "close", "volume"])
    writer.writeheader()
    writer.writerows(records)
    csv_bytes = buf.getvalue().encode("utf-8")

    resp = client.post(
        _url("/upload"),
        files={"file": ("test_data.csv", csv_bytes, "text/csv")},
        timeout=30,
    )
    _print_result("POST /upload", resp)
    return resp.status_code == 200


def main() -> None:
    global BASE_URL

    parser = argparse.ArgumentParser(description="Oil Risk Orchestrator API 测试")
    parser.add_argument("--base-url", default=BASE_URL, help="API 基础 URL")
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")

    print(f"🔗 测试目标: {BASE_URL}{API_PREFIX}\n")

    results: list[tuple[str, bool]] = []
    with httpx.Client() as client:
        results.append(("health", test_health(client)))
        results.append(("model_service_info", test_model_service_info(client)))
        results.append(("predict_mock", test_predict_mock(client)))
        results.append(("report_mock", test_report_mock(client)))
        results.append(("upload", test_upload(client)))

    print("=" * 50)
    print("测试结果汇总:")
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
    print(f"\n共 {len(results)} 项测试，通过 {passed} 项，失败 {len(results) - passed} 项")

    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
