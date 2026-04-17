from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from math import exp
from pathlib import Path
from typing import Any, Dict, List

from .feature_store import fetch_rows, FEATURE_STORE_DB


MODEL_DIR = Path(__file__).resolve().parents[3] / "data" / "models"


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + exp(-x))


def _fit_global_bias(rows: List[Dict[str, Any]]) -> float:
    # Uses implied probability trend and microstructure proxies as a baseline score.
    # No external ML dependency required.
    if not rows:
        return 0.0
    avg = sum(float(r["implied_prob"]) for r in rows) / len(rows)
    return max(-4.0, min(4.0, (avg - 0.5) * 8.0))


def load_training_rows(db_path: Path = FEATURE_STORE_DB) -> List[Dict[str, Any]]:
    return fetch_rows(db_path=db_path)


def train_baseline(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        raise ValueError("No training rows available")

    bias = _fit_global_bias(rows)
    market_means = defaultdict(list)
    for r in rows:
        market_means[r["market_id"]].append(float(r["implied_prob"]))

    market_params = {
        market_id: {
            "mean_prob": sum(vals) / len(vals),
            "count": len(vals),
        }
        for market_id, vals in market_means.items()
    }

    # Calibration: blend toward market mean to reduce over-confidence.
    calibration_alpha = 0.25

    artifact = {
        "model_name": "forecast_futures_baseline_v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "bias": bias,
        "calibration_alpha": calibration_alpha,
        "market_params": market_params,
        "training_row_count": len(rows),
    }

    digest = hashlib.sha256(json.dumps(artifact, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    artifact["model_version"] = f"ffb-v1-{digest}"
    return artifact


def predict(artifact: Dict[str, Any], market_id: str, implied_prob: float) -> Dict[str, float]:
    market_mean = artifact["market_params"].get(market_id, {}).get("mean_prob", implied_prob)
    raw_score = (implied_prob - 0.5) * 4 + artifact["bias"]
    raw_prob = _sigmoid(raw_score)
    calibrated = (1 - artifact["calibration_alpha"]) * raw_prob + artifact["calibration_alpha"] * market_mean
    calibrated = max(0.0, min(1.0, calibrated))

    # Simple confidence interval based on sample count for market.
    n = artifact["market_params"].get(market_id, {}).get("count", 1)
    radius = min(0.25, 1.0 / max(2.0, n ** 0.5))
    lo = max(0.0, calibrated - radius)
    hi = min(1.0, calibrated + radius)
    return {"model_prob": calibrated, "confidence_interval": [lo, hi]}


def save_artifact(artifact: Dict[str, Any], output_dir: Path = MODEL_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{artifact['model_version']}.json"
    out.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Forecast Futures baseline model")
    parser.add_argument("--db", default=str(FEATURE_STORE_DB))
    parser.add_argument("--output-dir", default=str(MODEL_DIR))
    args = parser.parse_args()

    rows = load_training_rows(Path(args.db))
    artifact = train_baseline(rows)
    path = save_artifact(artifact, Path(args.output_dir))
    print(json.dumps({
        "model_version": artifact["model_version"],
        "training_row_count": artifact["training_row_count"],
        "artifact_path": str(path),
    }, indent=2))


if __name__ == "__main__":
    main()
