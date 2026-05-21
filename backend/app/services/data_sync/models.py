from dataclasses import dataclass


@dataclass(frozen=True)
class RawIndicatorRow:
    indicator_code: str
    month: str
    value: str | float | int | None
    yoy: str | float | int | None = None
    mom: str | float | int | None = None
    trend_3m: str | float | int | None = None
    percentile_24m: str | float | int | None = None
    status: str | None = None
    source_ref: str | None = None
    line_number: int | None = None


@dataclass(frozen=True)
class SyncResult:
    imported: int
    months: list[str]
    sources: list[str]


class DataSyncError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))
