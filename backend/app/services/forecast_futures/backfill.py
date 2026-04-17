from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Iterable, List

from .contracts import validate_market_data_record, with_freshness
from .feature_store import upsert_rows, FEATURE_STORE_DB


def _load_input(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and "records" in payload:
            payload = payload["records"]
        return list(payload)

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    raise ValueError("Supported input types: .json, .csv")


def run_backfill(
    input_path: Path,
    report_path: Path,
    db_path: Path = FEATURE_STORE_DB,
    months: int = 12,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    start_ts = now - timedelta(days=max(1, months) * 30)

    source_rows = _load_input(input_path)
    accepted: List[Dict[str, Any]] = []
    per_market_counts = defaultdict(int)
    timestamps_per_market = defaultdict(list)

    for raw in source_rows:
        raw = with_freshness(raw, now=now)
        record = validate_market_data_record(raw)
        ts = datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
        if ts < start_ts:
            continue
        as_dict = record.as_dict()
        accepted.append(as_dict)
        per_market_counts[record.market_id] += 1
        timestamps_per_market[record.market_id].append(ts)

    inserted = upsert_rows(accepted, db_path=db_path)

    missing_intervals = {}
    for market_id, series in timestamps_per_market.items():
        series = sorted(series)
        gaps = []
        for a, b in zip(series, series[1:]):
            delta = (b - a).total_seconds()
            if delta > 3600:  # >1h gap in historical bars/ticks
                gaps.append({"from": a.isoformat(), "to": b.isoformat(), "seconds": int(delta)})
        missing_intervals[market_id] = gaps

    report = {
        "months_requested": months,
        "window_start": start_ts.isoformat(),
        "window_end": now.isoformat(),
        "source_records": len(source_rows),
        "accepted_records": len(accepted),
        "rows_upserted": inserted,
        "per_market_row_counts": dict(per_market_counts),
        "missing_interval_report": missing_intervals,
        "feature_store_db": str(db_path),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Forecast futures historical backfill")
    parser.add_argument("--input", required=True, help="CSV/JSON market history file")
    parser.add_argument("--report", default="backend/data/reports/backfill_report.json")
    parser.add_argument("--db", default=str(FEATURE_STORE_DB))
    parser.add_argument("--months", type=int, default=12)
    args = parser.parse_args()

    report = run_backfill(
        input_path=Path(args.input),
        report_path=Path(args.report),
        db_path=Path(args.db),
        months=args.months,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
