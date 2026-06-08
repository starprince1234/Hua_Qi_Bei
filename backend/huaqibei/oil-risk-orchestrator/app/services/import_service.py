"""Offline import seam for backtest runs and factor history files."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ValidationError

from ..repositories.protocols import BacktestRepository, FactorRepository
from ..schemas.intelligence_schema import (
    BacktestErrorsResponse,
    BacktestSeriesResponse,
    BacktestSummaryResponse,
    FactorHistoryResponse,
)

ProviderStatus = Literal["dry_run", "would_persist", "persisted"]
ImportRecord = dict[str, object]
ImportPayload = ImportRecord | list[ImportRecord]


@dataclass(frozen=True)
class BacktestImportPayload:
    """Validated backtest payload ready for repository persistence."""

    run_id: str
    summary: BacktestSummaryResponse
    series: BacktestSeriesResponse
    errors: BacktestErrorsResponse


@dataclass(frozen=True)
class FactorHistoryImportPayload:
    """Validated factor history payload ready for repository persistence."""

    run_id: str
    target: str
    history: FactorHistoryResponse


@dataclass(frozen=True)
class ImportResult:
    """Human-readable import result for M1 CLI output."""

    import_type: Literal["backtest", "factor_history"]
    run_id: str
    target: str
    date_range: str
    record_count: int
    provider_status: ProviderStatus
    validation_passed: bool
    payload: ImportRecord


class ImportService:
    """Validate offline CSV/JSON files and optionally call repository seams."""

    def __init__(
        self,
        backtest_repository: BacktestRepository | None = None,
        factor_repository: FactorRepository | None = None,
    ) -> None:
        self._backtest_repository: BacktestRepository | None = backtest_repository
        self._factor_repository: FactorRepository | None = factor_repository

    def import_backtest(
        self,
        file_path: str | Path,
        *,
        dry_run: bool = True,
        provider_status: str | None = None,
        model_version: str | None = None,
    ) -> ImportResult:
        """Load, validate, summarize, and optionally persist a backtest payload."""

        path = Path(file_path)
        raw_payload = self._load_payload(path)
        payload = self._validate_backtest_payload(raw_payload)

        if not dry_run and self._backtest_repository is not None:
            self._backtest_repository.save_backtest(
                payload.summary,
                payload.series,
                payload.errors,
                provider_status=provider_status or "offline_import",
                model_version=model_version,
            )

        status = self._provider_status(dry_run=dry_run, repository=self._backtest_repository)
        return ImportResult(
            import_type="backtest",
            run_id=payload.run_id,
            target=payload.summary.target,
            date_range=self._backtest_date_range(payload.summary, payload.series),
            record_count=len(payload.series.points),
            provider_status=status,
            validation_passed=True,
            payload={
                "summary": self._model_to_dict(payload.summary),
                "series": self._model_to_dict(payload.series),
                "errors": self._model_to_dict(payload.errors),
            },
        )

    def import_factor_history(
        self,
        file_path: str | Path,
        *,
        target: str = "Brent",
        dry_run: bool = True,
        provider_status: str | None = None,
    ) -> ImportResult:
        """Load, validate, summarize, and optionally persist factor history."""

        path = Path(file_path)
        raw_payload = self._load_payload(path)
        payload = self._validate_factor_history_payload(raw_payload, target=target)

        if not dry_run and self._factor_repository is not None:
            self._factor_repository.save_history(
                payload.target,
                payload.history,
                provider_status=provider_status or "offline_import",
                run_id=payload.run_id,
            )

        status = self._provider_status(dry_run=dry_run, repository=self._factor_repository)
        return ImportResult(
            import_type="factor_history",
            run_id=payload.run_id,
            target=payload.target,
            date_range=self._point_date_range(
                [point.date for point in payload.history.points]
            ),
            record_count=len(payload.history.points),
            provider_status=status,
            validation_passed=True,
            payload={"history": self._model_to_dict(payload.history)},
        )

    def format_result(self, result: ImportResult) -> str:
        """Render an import result as deterministic pretty JSON for scripts."""

        return json.dumps(
            {
                "import_type": result.import_type,
                "run_id": result.run_id,
                "summary": {
                    "count": result.record_count,
                    "target": result.target,
                    "date_range": result.date_range,
                    "provider_status": result.provider_status,
                    "validation_passed": result.validation_passed,
                },
                "would_persist": result.payload,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    def _load_payload(self, path: Path) -> ImportPayload:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return self._load_json(path)
        if suffix == ".csv":
            return self._load_csv(path)
        raise ValueError("Only .csv and .json input files are supported")

    def _load_json(self, path: Path) -> ImportPayload:
        with path.open("r", encoding="utf-8") as file:
            payload = cast(object, json.load(file))
        if isinstance(payload, dict):
            return cast(ImportRecord, payload)
        payload_items = cast(list[object], payload) if isinstance(payload, list) else []
        if payload_items and all(isinstance(item, dict) for item in payload_items):
            return cast(list[ImportRecord], payload)
        if isinstance(payload, list):
            raise ValueError("JSON import array must contain objects")
        else:
            raise ValueError("JSON import payload must be an object or array")

    def _load_csv(self, path: Path) -> list[ImportRecord]:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        if not rows:
            raise ValueError("CSV import file is empty")
        return [self._coerce_row(row) for row in rows]

    def _validate_backtest_payload(
        self,
        raw_payload: ImportPayload,
    ) -> BacktestImportPayload:
        payload = self._normalize_backtest_payload(raw_payload)
        try:
            summary = BacktestSummaryResponse.model_validate(
                {
                    "target": payload.get("target", "Brent"),
                    "window": payload.get("window", ""),
                    "metrics": payload.get("metrics", {}),
                    "stage_metrics": payload.get("stage_metrics", []),
                }
            )
            series = BacktestSeriesResponse.model_validate(
                {
                    "points": payload.get("points", []),
                    "events": payload.get("events", []),
                }
            )
            errors = BacktestErrorsResponse.model_validate({"bins": payload.get("bins", [])})
        except ValidationError as exc:
            raise ValueError(f"Backtest payload failed schema validation: {exc}") from exc

        run_id = self._deterministic_id(
            "backtest",
            summary.target,
            self._backtest_date_range(summary, series),
        )
        return BacktestImportPayload(
            run_id=run_id,
            summary=summary,
            series=series,
            errors=errors,
        )

    def _validate_factor_history_payload(
        self,
        raw_payload: ImportPayload,
        *,
        target: str,
    ) -> FactorHistoryImportPayload:
        payload = self._normalize_factor_payload(raw_payload)
        try:
            history = FactorHistoryResponse.model_validate(
                {
                    "categories": payload.get("categories", []),
                    "points": payload.get("points", []),
                }
            )
        except ValidationError as exc:
            raise ValueError(f"Factor history payload failed schema validation: {exc}") from exc

        date_range = self._point_date_range([point.date for point in history.points])
        run_id = self._deterministic_id("factor_history", target, date_range)
        return FactorHistoryImportPayload(run_id=run_id, target=target, history=history)

    def _normalize_backtest_payload(
        self,
        raw_payload: ImportPayload,
    ) -> ImportRecord:
        if isinstance(raw_payload, dict):
            return raw_payload
        default_window = self._point_date_range(row.get("date") for row in raw_payload)
        return {
            "target": raw_payload[0].get("target", "Brent"),
            "window": raw_payload[0].get("window", default_window),
            "metrics": self._parse_json_cell(raw_payload[0].get("metrics"), default={}),
            "stage_metrics": self._parse_json_cell(raw_payload[0].get("stage_metrics"), default=[]),
            "points": self._rows_by_record_type(raw_payload, "point"),
            "events": self._rows_by_record_type(raw_payload, "event"),
            "bins": self._rows_by_record_type(raw_payload, "bin"),
        }

    def _normalize_factor_payload(
        self,
        raw_payload: ImportPayload,
    ) -> ImportRecord:
        if isinstance(raw_payload, dict):
            return raw_payload
        categories = [
            "inventory",
            "geo",
            "macro",
            "supply_demand",
            "technical",
        ]
        return {"categories": categories, "points": raw_payload}

    def _rows_by_record_type(
        self,
        rows: list[ImportRecord],
        record_type: str,
    ) -> list[ImportRecord]:
        typed_rows = [row for row in rows if row.get("record_type") == record_type]
        if typed_rows:
            return [self._drop_import_columns(row) for row in typed_rows]
        if record_type == "point":
            return [
                self._drop_import_columns(row)
                for row in rows
                if {
                    "actual_price",
                    "predicted_price",
                    "lower_price",
                    "upper_price",
                }.issubset(row)
            ]
        return []

    def _drop_import_columns(self, row: ImportRecord) -> ImportRecord:
        return {
            key: value
            for key, value in row.items()
            if key
            not in {
                "record_type",
                "target",
                "window",
                "metrics",
                "stage_metrics",
                "categories",
            }
            and value is not None
        }

    def _coerce_row(self, row: dict[str, str | None]) -> ImportRecord:
        return {key: self._coerce_value(value) for key, value in row.items()}

    def _coerce_value(self, value: str | None) -> object:
        if value is None:
            return None
        stripped = value.strip()
        if stripped == "":
            return None
        lowered = stripped.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if stripped.startswith(("{", "[")):
            return self._parse_json_cell(stripped, default=stripped)
        try:
            if any(char in stripped for char in [".", "e", "E"]):
                return float(stripped)
            return int(stripped)
        except ValueError:
            return stripped

    def _parse_json_cell(self, value: object, *, default: object) -> object:
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return cast(object, value)
        try:
            return cast(object, json.loads(str(value)))
        except json.JSONDecodeError:
            return default

    def _backtest_date_range(
        self,
        summary: BacktestSummaryResponse,
        series: BacktestSeriesResponse,
    ) -> str:
        if summary.window:
            return summary.window
        return self._point_date_range([point.date for point in series.points])

    def _point_date_range(self, dates: Iterable[object]) -> str:
        normalized = sorted(str(value) for value in dates if value)
        if not normalized:
            return "unknown"
        return f"{normalized[0]}/{normalized[-1]}"

    def _deterministic_id(self, import_type: str, target: str, date_range: str) -> str:
        digest = hashlib.sha256(
            f"{import_type}:{target}:{date_range}".encode("utf-8")
        ).hexdigest()
        return f"{import_type}_{digest[:16]}"

    def _provider_status(self, *, dry_run: bool, repository: object | None) -> ProviderStatus:
        if dry_run:
            return "dry_run"
        if repository is None:
            return "would_persist"
        return "persisted"

    def _model_to_dict(self, model: BaseModel) -> ImportRecord:
        return cast(ImportRecord, model.model_dump())
