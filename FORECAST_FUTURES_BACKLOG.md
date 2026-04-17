FORECAST FUTURES - CARD DECOMPOSITION + ACCEPTANCE CRITERIA

Parent cards reviewed: CARD-006..CARD-010
Result: All 5 were Medium/Large and split into small executable backlog cards.

PARENT TRACKING
- CARD-006 Data ingestion and feature store (split)
- CARD-007 Forecast model service (split)
- CARD-008 Backtesting and evaluation (split)
- CARD-009 Real-time signal engine (split)
- CARD-010 Forecast Futures UI (split)

CHILD CARDS

CARD-011 | Backlog | Define market data schema + feature store contracts
AC:
1) Canonical schema includes market_id, event_id, timestamp, implied_prob, volume, spread, depth, source, freshness_seconds.
2) JSON schema validation exists and rejects malformed records.
3) Contract doc committed and referenced by ingestion + model services.

CARD-012 | Backlog | Build historical backfill pipeline
AC:
1) Backfill job imports at least 12 months (or max available) for selected markets.
2) Idempotent rerun does not duplicate rows.
3) Job output includes per-market row counts + missing interval report.

CARD-013 | Backlog | Build live market ingestion pipeline
AC:
1) Live ingest updates records at configured polling/stream interval.
2) freshness_seconds computed on each record.
3) Retry with exponential backoff on transient failures.

CARD-014 | Backlog | Add data quality checks for ingestion
AC:
1) DQ checks cover nulls, monotonic timestamps, out-of-range probabilities, negative volume/spread/depth.
2) Failed checks produce structured error logs.
3) Daily DQ summary artifact generated.

CARD-015 | Backlog | Train baseline probability model
AC:
1) Baseline model trains from feature store and outputs calibrated probabilities in [0,1].
2) Model artifact is versioned.
3) Training run is reproducible via single command.

CARD-016 | Backlog | Add calibration + confidence interval module
AC:
1) Calibration method implemented (Platt or isotonic) and selectable by config.
2) Prediction response includes confidence interval bounds.
3) Calibration error metric logged per run.

CARD-017 | Backlog | Expose model inference API
AC:
1) Endpoint returns market_prob, model_prob, confidence_interval, model_version, computed_at.
2) p95 response time <= 250ms on cached path.
3) Input validation rejects unknown market IDs with typed error.

CARD-018 | Backlog | Build historical backtest engine
AC:
1) Backtest runs across configurable date range and market subset.
2) Reports Brier score + log loss.
3) Net edge includes fees/slippage parameters.

CARD-019 | Backlog | Build walk-forward evaluation pipeline
AC:
1) Time-sliced train/validate/test windows implemented with no leakage.
2) Outputs calibration curve and drift indicators.
3) Run summary compares model vs market baseline.

CARD-020 | Backlog | Implement large-move detector
AC:
1) Detector flags moves by configurable thresholds (absolute and z-score).
2) Emits event payload with movement context and freshness.
3) Duplicate suppression window prevents alert spam.

CARD-021 | Backlog | Implement edge/ranking engine
AC:
1) Rank score combines edge, confidence, liquidity, spread quality, recency.
2) Low-tradeability markets are penalized or gated.
3) Ranking output includes score breakdown fields.

CARD-022 | Backlog | Add latency + stale-signal guardrails
AC:
1) End-to-end latency measured from ingest to emitted signal.
2) Signals older than freshness threshold are auto-suppressed.
3) Monitoring exposes p50/p95 latency and stale-drop counts.

CARD-023 | Backlog | Build Forecast Futures list screen
AC:
1) List shows top opportunities with market move, model edge, confidence, freshness.
2) Supports sort by score, recency, and most-clicked.
3) Empty/loading/error states implemented.

CARD-024 | Backlog | Build Forecast detail screen
AC:
1) Detail view shows probability trend chart + scenario driver tags.
2) Displays market_prob vs model_prob with confidence interval.
3) Last updated timestamp visible.

CARD-025 | Backlog | Add trade deep-link + click telemetry
AC:
1) "Open in Kalshi" deep-link launches target market reliably.
2) Click telemetry records unique clicks per market for trending.
3) Most-clicked module renders from telemetry with time decay window.

Suggested execution order:
CARD-011 -> 012 -> 013 -> 014 -> 015 -> 016 -> 017 -> 018 -> 019 -> 020 -> 021 -> 022 -> 023 -> 024 -> 025
