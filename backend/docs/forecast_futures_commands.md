# Forecast Futures Commands (Cards 011-015)

Run from `backend/`:

1) Historical backfill (CARD-012)
`python -m app.services.forecast_futures.backfill --input data/sample_history.json --report data/reports/backfill_report.json --months 12`

2) Live ingestion (CARD-013)
`python -m app.services.forecast_futures.live_ingest --url https://example.com/markets/live --iterations 1 --poll 15 --report data/reports/live_ingest_report.json`

3) Data quality checks (CARD-014)
`python -m app.services.forecast_futures.data_quality --db data/forecast_feature_store.db --limit 50000`

4) Train baseline model artifact (CARD-015)
`python -m app.services.forecast_futures.train --db data/forecast_feature_store.db --output-dir data/models`

The training command is reproducible: same dataset + code yields deterministic model version hash.
