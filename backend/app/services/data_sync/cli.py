import argparse

from app.core.database import SessionLocal
from app.services.data_sync.csv_file import load_csv_rows
from app.services.data_sync.models import DataSyncError
from app.services.data_sync.official_latest import load_official_latest_rows
from app.services.data_sync.service import prune_months_after, sync_indicator_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync real macro indicator data from CSV files.")
    parser.add_argument("path", nargs="?", help="CSV file or directory containing CSV files")
    parser.add_argument("--official-latest", action="store_true", help="sync the bundled latest official public snapshot")
    parser.add_argument("--prune-newer", action="store_true", help="remove local months newer than the synced snapshot")
    args = parser.parse_args()
    if not args.official_latest and not args.path:
        parser.error("path is required unless --official-latest is used")

    try:
        rows = load_official_latest_rows() if args.official_latest else load_csv_rows(args.path)
        with SessionLocal() as db:
            result = sync_indicator_rows(db, rows)
            if args.prune_newer and result.months:
                deleted = prune_months_after(db, result.months[-1])
                print(f"pruned={deleted}")
    except DataSyncError as exc:
        for error in exc.errors:
            print(error)
        return 1

    print(f"imported={result.imported}")
    print(f"months={','.join(result.months)}")
    print(f"sources={','.join(result.sources)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
