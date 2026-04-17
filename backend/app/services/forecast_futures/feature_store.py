from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Dict, Any, List

FEATURE_STORE_DB = Path(__file__).resolve().parents[3] / "data" / "forecast_feature_store.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS market_data (
  market_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  implied_prob REAL NOT NULL,
  volume REAL NOT NULL,
  spread REAL NOT NULL,
  depth REAL NOT NULL,
  source TEXT NOT NULL,
  freshness_seconds INTEGER NOT NULL,
  PRIMARY KEY (market_id, timestamp)
);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or FEATURE_STORE_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA_SQL)
    conn.commit()
    return conn


def upsert_rows(rows: Iterable[Dict[str, Any]], db_path: Path | None = None) -> int:
    rows = list(rows)
    if not rows:
        return 0

    with connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO market_data (
                market_id, event_id, timestamp, implied_prob, volume,
                spread, depth, source, freshness_seconds
            ) VALUES (:market_id, :event_id, :timestamp, :implied_prob, :volume,
                      :spread, :depth, :source, :freshness_seconds)
            ON CONFLICT(market_id, timestamp) DO UPDATE SET
                event_id=excluded.event_id,
                implied_prob=excluded.implied_prob,
                volume=excluded.volume,
                spread=excluded.spread,
                depth=excluded.depth,
                source=excluded.source,
                freshness_seconds=excluded.freshness_seconds
            """,
            rows,
        )
        conn.commit()
    return len(rows)


def fetch_rows(db_path: Path | None = None, limit: int | None = None) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        cursor = conn.cursor()
        q = "SELECT market_id, event_id, timestamp, implied_prob, volume, spread, depth, source, freshness_seconds FROM market_data ORDER BY timestamp"
        if limit:
            q += f" LIMIT {int(limit)}"
        cursor.execute(q)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
