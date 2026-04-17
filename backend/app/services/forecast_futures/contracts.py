from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "forecast_market_data.schema.json"
CONTRACT_DOC_PATH = Path(__file__).resolve().parents[4] / "docs" / "forecast_futures_contract.md"


@dataclass
class MarketDataRecord:
    market_id: str
    event_id: str
    timestamp: str
    implied_prob: float
    volume: float
    spread: float
    depth: float
    source: str
    freshness_seconds: int

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "MarketDataRecord":
        return cls(
            market_id=str(payload.get("market_id", "")).strip(),
            event_id=str(payload.get("event_id", "")).strip(),
            timestamp=str(payload.get("timestamp", "")).strip(),
            implied_prob=float(payload.get("implied_prob", 0.0)),
            volume=float(payload.get("volume", 0.0)),
            spread=float(payload.get("spread", 0.0)),
            depth=float(payload.get("depth", 0.0)),
            source=str(payload.get("source", "")).strip(),
            freshness_seconds=int(payload.get("freshness_seconds", 0)),
        )

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_schema() -> Dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_market_data_record(payload: Dict[str, Any]) -> MarketDataRecord:
    schema = _load_schema()
    required = schema["required"]

    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    record = MarketDataRecord.from_dict(payload)

    if not record.market_id:
        raise ValueError("market_id cannot be empty")
    if not record.event_id:
        raise ValueError("event_id cannot be empty")
    if not record.source:
        raise ValueError("source cannot be empty")

    try:
        datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be valid ISO8601") from exc

    if not (0.0 <= record.implied_prob <= 1.0):
        raise ValueError("implied_prob must be between 0 and 1")
    if record.volume < 0:
        raise ValueError("volume must be >= 0")
    if record.spread < 0:
        raise ValueError("spread must be >= 0")
    if record.depth < 0:
        raise ValueError("depth must be >= 0")
    if record.freshness_seconds < 0:
        raise ValueError("freshness_seconds must be >= 0")

    return record


def with_freshness(payload: Dict[str, Any], now: datetime | None = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    ts = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00"))
    freshness = int((now - ts).total_seconds())
    payload = dict(payload)
    payload["freshness_seconds"] = max(0, freshness)
    return payload
