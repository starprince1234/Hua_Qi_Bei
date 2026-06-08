"""CLI for offline factor history imports."""

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
class ImportFactorHistoryArgs:
    """Typed CLI arguments for factor history import preview."""

    file: str
    target: str
    dry_run: bool


def parse_args() -> ImportFactorHistoryArgs:
    parser = argparse.ArgumentParser(description="Validate and preview factor history imports")
    _ = parser.add_argument("--file", required=True, help="Path to a .csv or .json factor history file")
    _ = parser.add_argument(
        "--target",
        default="Brent",
        help="Imported target name used for deterministic run ID generation",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print what would be persisted without saving",
    )
    namespace = parser.parse_args()
    file_path = cast(str, namespace.file)
    target = cast(str, namespace.target)
    dry_run = cast(bool, namespace.dry_run)
    return ImportFactorHistoryArgs(
        file=file_path,
        target=target,
        dry_run=dry_run,
    )


def main() -> int:
    args = parse_args()
    service = ImportService()
    result = service.import_factor_history(
        args.file,
        target=args.target,
        dry_run=args.dry_run,
    )
    print(service.format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
