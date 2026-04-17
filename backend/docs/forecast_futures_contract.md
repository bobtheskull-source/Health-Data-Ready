# Forecast Futures Contract (CARD-011)

This contract is shared by ingestion, feature store, and model services.

## Canonical Record Schema

Required fields:
- market_id (string)
- event_id (string)
- timestamp (ISO8601)
- implied_prob (float, 0..1)
- volume (float, >=0)
- spread (float, >=0)
- depth (float, >=0)
- source (string)
- freshness_seconds (int, >=0)

Schema file:
- `backend/app/schemas/forecast_market_data.schema.json`

Validation helper:
- `app.services.forecast_futures.contracts.validate_market_data_record`

## Integration Points

Ingestion services use this contract before writes:
- `app.services.forecast_futures.backfill.run_backfill`
- `app.services.forecast_futures.live_ingest.run_live_ingestion`

Model training expects this schema from feature store reads:
- `app.services.forecast_futures.train.load_training_rows`
