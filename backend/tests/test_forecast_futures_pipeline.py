from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.forecast_futures.backfill import run_backfill
from app.services.forecast_futures.contracts import validate_market_data_record
from app.services.forecast_futures.data_quality import run_dq_checks
from app.services.forecast_futures.feature_store import fetch_rows
from app.services.forecast_futures.train import train_baseline, predict


def _sample_record(ts):
    return {
        "market_id": "mkt-1",
        "event_id": "evt-1",
        "timestamp": ts.isoformat(),
        "implied_prob": 0.61,
        "volume": 1200.0,
        "spread": 0.02,
        "depth": 800.0,
        "source": "test",
        "freshness_seconds": 0,
    }


def test_contract_validation_accepts_valid_record():
    rec = validate_market_data_record(_sample_record(datetime.now(timezone.utc)))
    assert rec.market_id == "mkt-1"


def test_backfill_is_idempotent_and_generates_report(tmp_path):
    now = datetime.now(timezone.utc)
    records = [
        _sample_record(now - timedelta(days=1)),
        _sample_record(now - timedelta(hours=1)),
    ]
    in_file = tmp_path / "history.json"
    in_file.write_text(__import__("json").dumps(records), encoding="utf-8")

    report_file = tmp_path / "report.json"
    db_path = tmp_path / "feature_store.db"

    first = run_backfill(in_file, report_file, db_path=db_path, months=12)
    second = run_backfill(in_file, report_file, db_path=db_path, months=12)

    rows = fetch_rows(db_path=db_path)
    assert first["rows_upserted"] == 2
    assert second["rows_upserted"] == 2
    assert len(rows) == 2
    assert report_file.exists()


def test_dq_checks_catch_out_of_range_probability():
    bad = _sample_record(datetime.now(timezone.utc))
    bad["implied_prob"] = 2.0
    result = run_dq_checks([bad])
    assert result["summary"]["failed_records"] == 1


def test_training_outputs_calibrated_probability_range():
    rows = []
    now = datetime.now(timezone.utc)
    for i in range(10):
        rec = _sample_record(now - timedelta(minutes=i))
        rec["implied_prob"] = 0.4 + (i * 0.01)
        rows.append(rec)

    artifact = train_baseline(rows)
    pred = predict(artifact, "mkt-1", implied_prob=0.58)

    assert 0 <= pred["model_prob"] <= 1
    lo, hi = pred["confidence_interval"]
    assert 0 <= lo <= hi <= 1
    assert artifact["model_version"].startswith("ffb-v1-")
