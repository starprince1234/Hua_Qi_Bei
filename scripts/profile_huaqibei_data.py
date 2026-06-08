from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile Hua Qi Bei Excel source data.")
    parser.add_argument("--data-dir", required=True, help="Directory containing raw/ and processed/.")
    parser.add_argument("--output", required=True, help="Output JSON report path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir)
    output = Path(args.output)
    report: dict[str, Any] = {"files": []}

    for path in sorted(data_dir.rglob("*")):
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            continue
        entry: dict[str, Any] = {
            "path": str(path.relative_to(data_dir)).replace("\\", "/"),
            "size": path.stat().st_size,
            "sheets": [],
        }
        try:
            workbook = pd.ExcelFile(path)
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"{type(exc).__name__}: {exc}"
            report["files"].append(entry)
            continue

        for sheet_name in workbook.sheet_names:
            try:
                frame = workbook.parse(sheet_name)
            except Exception as exc:  # noqa: BLE001
                entry["sheets"].append(
                    {"name": sheet_name, "error": f"{type(exc).__name__}: {exc}"}
                )
                continue
            sheet: dict[str, Any] = {
                "name": sheet_name,
                "rows": int(len(frame)),
                "columns": [str(column) for column in frame.columns],
                "date_candidates": _date_candidates(frame),
                "numeric_columns": _numeric_columns(frame),
            }
            entry["sheets"].append(sheet)
        report["files"].append(entry)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def _date_candidates(frame: pd.DataFrame) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for column in frame.columns:
        name = str(column)
        if not any(token in name.lower() for token in ["date", "time", "日期", "时间"]):
            continue
        series = pd.to_datetime(frame[column], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            continue
        candidates.append(
            {
                "column": name,
                "valid_rows": int(valid.size),
                "min": valid.min().date().isoformat(),
                "max": valid.max().date().isoformat(),
            }
        )
    return candidates


def _numeric_columns(frame: pd.DataFrame) -> list[dict[str, Any]]:
    numeric: list[dict[str, Any]] = []
    for column in frame.columns:
        series = pd.to_numeric(frame[column], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            continue
        numeric.append(
            {
                "column": str(column),
                "valid_rows": int(valid.size),
                "missing_rows": int(series.isna().sum()),
                "min": _round(valid.min()),
                "max": _round(valid.max()),
                "mean": _round(valid.mean()),
            }
        )
    return numeric[:80]


def _round(value: float) -> float:
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
