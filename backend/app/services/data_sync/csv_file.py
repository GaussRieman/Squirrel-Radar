import csv
from io import StringIO
from pathlib import Path

from app.services.data_sync.models import DataSyncError, RawIndicatorRow

REQUIRED_HEADERS = {
    "indicator_code",
    "month",
    "value",
    "yoy",
    "mom",
    "trend_3m",
    "percentile_24m",
    "status",
}


def load_csv_rows(path: str | Path) -> list[RawIndicatorRow]:
    source_path = Path(path).expanduser()
    files = _resolve_files(source_path)
    rows: list[RawIndicatorRow] = []
    errors: list[str] = []
    for file_path in files:
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not REQUIRED_HEADERS.issubset(set(reader.fieldnames)):
                errors.append(f"{file_path}: CSV headers are invalid")
                continue
            for line_number, item in enumerate(reader, start=2):
                rows.append(
                    RawIndicatorRow(
                        indicator_code=item.get("indicator_code", ""),
                        month=item.get("month", ""),
                        value=item.get("value"),
                        yoy=item.get("yoy"),
                        mom=item.get("mom"),
                        trend_3m=item.get("trend_3m"),
                        percentile_24m=item.get("percentile_24m"),
                        status=item.get("status"),
                        source_ref=str(file_path),
                        line_number=line_number,
                    )
                )
    if errors:
        raise DataSyncError(errors)
    return rows


def load_csv_content(content: str, source_ref: str = "uploaded csv") -> list[RawIndicatorRow]:
    reader = csv.DictReader(StringIO(content))
    if not reader.fieldnames or not REQUIRED_HEADERS.issubset(set(reader.fieldnames)):
        raise DataSyncError([f"{source_ref}: CSV headers are invalid"])
    return [
        RawIndicatorRow(
            indicator_code=item.get("indicator_code", ""),
            month=item.get("month", ""),
            value=item.get("value"),
            yoy=item.get("yoy"),
            mom=item.get("mom"),
            trend_3m=item.get("trend_3m"),
            percentile_24m=item.get("percentile_24m"),
            status=item.get("status"),
            source_ref=source_ref,
            line_number=line_number,
        )
        for line_number, item in enumerate(reader, start=2)
    ]


def _resolve_files(path: Path) -> list[Path]:
    if not path.exists():
        raise DataSyncError([f"{path}: path does not exist"])
    if path.is_file():
        if path.suffix.lower() != ".csv":
            raise DataSyncError([f"{path}: expected a .csv file"])
        return [path]
    files = sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".csv")
    if not files:
        raise DataSyncError([f"{path}: no .csv files found"])
    return files
