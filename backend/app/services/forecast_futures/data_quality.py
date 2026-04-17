from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .feature_store import fetch_rows, FEATURE_STORE_DB


DQ_LOG_PATH = Path(__file__).resolve().parents[3] / "data" / "reports" / "dq_failures.jsonl"


def run_dq_checks(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    by_market = defaultdict(list)

    for row in rows:
        by_market[row["market_id"]].append(row)

    for market_id, market_rows in by_market.items():
        ordered = sorted(market_rows, key=lambda r: r["timestamp"])
        for idx, r in enumerate(ordered):
            checks = []
            if any(r.get(k) in (None, "") for k in ["market_id", "event_id", "timestamp", "source"]):
                checks.append("null_or_empty_required_field")
            if not (0 <= float(r["implied_prob"]) <= 1):
                checks.append("implied_prob_out_of_range")
            if float(r["volume"]) < 0:
                checks.append("negative_volume")
            if float(r["spread"]) < 0:
                checks.append("negative_spread")
            if float(r["depth"]) < 0:
                checks.append("negative_depth")

            if idx > 0 and ordered[idx - 1]["timestamp"] > r["timestamp"]:
                checks.append("non_monotonic_timestamp")

            if checks:
                failures.append({
                    "market_id": market_id,
                    "timestamp": r["timestamp"],
                    "checks": checks,
                    "record": r,
                })

    summary = {
        "checked_records": len(rows),
        "failed_records": len(failures),
        "failure_rate": (len(failures) / len(rows)) if rows else 0.0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"summary": summary, "failures": failures}


def write_dq_artifacts(result: Dict[str, Any], log_path: Path = DQ_LOG_PATH) -> Dict[str, str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        for failure in result["failures"]:
            f.write(json.dumps(failure) + "\n")

    daily_name = f"dq_summary_{datetime.now(timezone.utc).date().isoformat()}.json"
    summary_path = log_path.parent / daily_name
    summary_path.write_text(json.dumps(result["summary"], indent=2), encoding="utf-8")

    return {"structured_log": str(log_path), "daily_summary": str(summary_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Forecast Futures ingestion DQ checks")
    parser.add_argument("--db", default=str(FEATURE_STORE_DB))
    parser.add_argument("--limit", type=int, default=50000)
    args = parser.parse_args()

    rows = fetch_rows(db_path=Path(args.db), limit=args.limit)
    result = run_dq_checks(rows)
    artifacts = write_dq_artifacts(result)
    print(json.dumps({"summary": result["summary"], "artifacts": artifacts}, indent=2))


if __name__ == "__main__":
    main()
