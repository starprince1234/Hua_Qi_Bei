"""CLI for offline backtest imports."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.import_service import ImportService  # pyright: ignore[reportImplicitRelativeImport]  # noqa: E402


@dataclass(frozen=True)
class ImportBacktestArgs:
    """Typed CLI arguments for backtest import preview."""

    file: str
    dry_run: bool
    model_version: str | None


def parse_args() -> ImportBacktestArgs:
    parser = argparse.ArgumentParser(description="Validate and preview backtest imports")
    _ = parser.add_argument("--file", required=True, help="Path to a .csv or .json backtest file")
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print what would be persisted without saving",
    )
    _ = parser.add_argument("--model-version", default=None, help="Optional imported model version")
    namespace = parser.parse_args()
    file_path = cast(str, namespace.file)
    dry_run = cast(bool, namespace.dry_run)
    model_version = cast(str | None, namespace.model_version)
    return ImportBacktestArgs(
        file=file_path,
        dry_run=dry_run,
        model_version=model_version,
    )


def main() -> int:
    args = parse_args()
    service = ImportService()
    result = service.import_backtest(
        args.file,
        dry_run=args.dry_run,
        model_version=args.model_version,
    )
    print(service.format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
