from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import httpx

from .contracts import validate_market_data_record, with_freshness
from .feature_store import upsert_rows, FEATURE_STORE_DB


def _fetch_json(client: httpx.Client, url: str, retries: int = 3, backoff_seconds: float = 0.5) -> List[Dict[str, Any]]:
    for attempt in range(retries + 1):
        try:
            resp = client.get(url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "records" in data:
                data = data["records"]
            return list(data)
        except Exception:
            if attempt >= retries:
                raise
            time.sleep(backoff_seconds * (2 ** attempt))
    return []


def run_live_ingestion(
    source_url: str,
    db_path: Path = FEATURE_STORE_DB,
    max_iterations: int = 1,
    poll_interval_seconds: int = 15,
    report_path: Path | None = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    total_upserts = 0
    total_valid = 0

    with httpx.Client() as client:
        for _ in range(max_iterations):
            rows = _fetch_json(client, source_url)
            validated = []
            for row in rows:
                row = with_freshness(row, now=datetime.now(timezone.utc))
                rec = validate_market_data_record(row)
                validated.append(rec.as_dict())
            total_valid += len(validated)
            total_upserts += upsert_rows(validated, db_path=db_path)
            if max_iterations > 1:
                time.sleep(poll_interval_seconds)

    report = {
        "source_url": source_url,
        "iterations": max_iterations,
        "poll_interval_seconds": poll_interval_seconds,
        "validated_records": total_valid,
        "rows_upserted": total_upserts,
        "run_completed_at": now.isoformat(),
        "feature_store_db": str(db_path),
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Forecast futures live ingestion")
    parser.add_argument("--url", required=True, help="Live market data endpoint returning JSON records")
    parser.add_argument("--db", default=str(FEATURE_STORE_DB))
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--poll", type=int, default=15)
    parser.add_argument("--report", default="backend/data/reports/live_ingest_report.json")
    args = parser.parse_args()

    report = run_live_ingestion(
        source_url=args.url,
        db_path=Path(args.db),
        max_iterations=args.iterations,
        poll_interval_seconds=args.poll,
        report_path=Path(args.report),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
