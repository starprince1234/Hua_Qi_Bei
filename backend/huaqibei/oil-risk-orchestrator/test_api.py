#!/usr/bin/env python3
"""
Simple integration test script for the Oil Risk Orchestrator API.

Usage:
    python test_api.py [--base-url http://localhost:8000]
"""
from __future__ import annotations

import argparse
import io
import json
import sys

import requests

BASE_URL = "http://localhost:8000"

SAMPLE_CSV = """\
date,crude_price,usd_index,vix,opec_production,global_demand
2024-01-02,76.50,101.2,13.5,30.1,101.5
2024-01-03,77.10,101.0,13.2,30.1,101.6
2024-01-04,76.80,101.3,14.0,30.2,101.4
2024-01-05,78.20,100.8,13.8,30.0,101.8
2024-01-08,79.10,100.5,12.9,30.0,102.0
2024-01-09,78.70,100.7,13.1,30.1,101.9
2024-01-10,80.30,100.2,12.5,29.9,102.3
2024-01-11,81.00,99.8,12.0,29.8,102.5
2024-01-12,80.50,100.0,12.3,29.9,102.4
2024-01-15,79.80,100.4,13.5,30.0,102.0
2024-01-16,80.10,100.1,13.0,30.0,102.2
2024-01-17,82.00,99.5,11.8,29.7,102.8
2024-01-18,81.50,99.7,12.1,29.8,102.6
2024-01-19,83.00,99.2,11.5,29.6,103.0
2024-01-22,83.50,99.0,11.2,29.5,103.2
"""

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def test_health(base_url: str) -> bool:
    print("=== Health Check ===")
    try:
        r = requests.get(f"{base_url}/health", timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert body.get("status") == "ok", f"status != ok: {body}"
        print(f"  {PASS}: status=ok, version={body.get('version')}")
        return True
    except Exception as e:
        print(f"  {FAIL}: {e}")
        return False


def test_upload(base_url: str) -> str | None:
    print("\n=== Upload ===")
    try:
        files = {"file": ("sample.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
        r = requests.post(f"{base_url}/upload", files=files, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("success") is True, f"success != true: {body}"
        file_id = body["data"]["file_id"]
        print(f"  {PASS}: file_id={file_id}, size={body['data']['size']} bytes")
        return file_id
    except Exception as e:
        print(f"  {FAIL}: {e}")
        return None


def test_predict(base_url: str, file_id: str) -> bool:
    print("\n=== Predict ===")
    payload = {
        "file_id": file_id,
        "horizon": 7,
        "include_explainability": True,
        "include_knowledge_graph": False,
        "report_style": "general",
        "industries": ["aviation", "shipping", "chemical"],
    }
    try:
        r = requests.post(f"{base_url}/predict", json=payload, timeout=60)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "predictions" in body, "Missing 'predictions' in response"
        assert "risk_level" in body, "Missing 'risk_level' in response"
        assert len(body["predictions"]) == 7, f"Expected 7 predictions, got {len(body['predictions'])}"
        print(f"  {PASS}: risk_level={body['risk_level']}, predictions[0]={body['predictions'][0]:.2f}")
        print(f"         factors={len(body.get('factor_contributions', []))}, "
              f"industries={len(body.get('industry_impacts', []))}")
        return True
    except Exception as e:
        print(f"  {FAIL}: {e}")
        return False


def test_report(base_url: str, file_id: str) -> bool:
    print("\n=== Report ===")
    try:
        r = requests.get(f"{base_url}/report/{file_id}", timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "summary" in body, "Missing 'summary' in report"
        print(f"  {PASS}: style={body.get('style')}, title={body.get('title')}")
        return True
    except Exception as e:
        print(f"  {FAIL}: {e}")
        return False


def test_model_placeholder(base_url: str) -> bool:
    print("\n=== Model Placeholder Status ===")
    try:
        r = requests.get(f"{base_url}/model-placeholder/status", timeout=10)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        print(f"  {PASS}: status={body.get('status')}")
        return True
    except Exception as e:
        print(f"  {FAIL}: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Oil Risk Orchestrator API smoke tests")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    results: list[bool] = []

    results.append(test_health(base))
    results.append(test_model_placeholder(base))

    file_id = test_upload(base)
    results.append(file_id is not None)

    if file_id:
        results.append(test_predict(base, file_id))
        results.append(test_report(base, file_id))

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
