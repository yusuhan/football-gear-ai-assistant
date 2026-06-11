#!/usr/bin/env python3
"""Reset local runtime data while preserving a timestamped SQLite backup."""

import argparse
import os
import sys
from pathlib import Path

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIRECTORY))

from app.core.config import Settings  # noqa: E402
from app.services.demo_data_service import DemoDataService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back up and reset Football Gear AI Assistant demo data.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation for the destructive reset.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the default SQLite backup.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Override DATABASE_PATH for this reset.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.yes:
        print("Reset cancelled: pass --yes to confirm.", file=sys.stderr)
        return 2

    os.chdir(ROOT_DIRECTORY)
    settings = Settings()
    if args.database:
        settings = settings.model_copy(update={"database_path": args.database})

    result = DemoDataService(settings).reset(create_backup=not args.no_backup)
    print(f"Database reset: {result.database_path}")
    print(f"Backup: {result.backup_path or 'skipped'}")
    print(f"Cleared rows: {sum(result.cleared_rows.values())}")
    print(f"Seeded products: {result.product_count}")
    print(f"Bootstrap users: {result.operations_user_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
