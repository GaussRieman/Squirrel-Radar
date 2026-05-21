# Real Data Sync Design

## Goal

Connect Squirrel Radar to real macro data without changing the dashboard or Agent contract. The dashboard, rules engine, and Agent should continue reading from `indicator_data`; only the ingestion layer changes.

## Scope

First version adds a reusable sync layer with a local CSV adapter. This gives us a production-shaped path today:

1. Export or download real source data into the existing CSV schema.
2. Run a backend sync API or CLI command.
3. Upsert `indicator_data`.
4. Re-evaluate touched months so snapshots, rules, dashboard, and Agent all update.

Official-source adapters such as PBOC, NBS, Wind, Choice, Tushare, or AkShare can later implement the same adapter interface.

## Data Contract

Canonical rows use the current import shape:

```csv
indicator_code,month,value,yoy,mom,trend_3m,percentile_24m,status
m2_yoy,2026-05,8.9,8.9,0.1,8.8,72,strong
```

`indicator_code` must match `indicator_definitions.code`. `month` is `YYYY-MM`. `status` defaults to `neutral` when omitted.

## Components

- `data_sync.models`: typed sync row, result, and error structures.
- `data_sync.adapters.csv_file`: reads one CSV file or every CSV file in a directory.
- `data_sync.service`: validates rows, upserts data, commits once, then evaluates every touched month.
- API endpoint: `POST /api/data-sync/local-csv` for local development and manual operations.
- CLI module: `python -m app.services.data_sync.cli <path>` for scheduled jobs or scripts.

## Error Handling

The sync layer validates all rows before writing. If any row is invalid, it returns line-level errors and does not partially import. Unknown indicator codes, malformed months, and non-numeric values are hard failures.

## Testing

Unit tests cover importing a CSV file, updating an existing row, directory import, evaluation trigger, and invalid input rollback.

