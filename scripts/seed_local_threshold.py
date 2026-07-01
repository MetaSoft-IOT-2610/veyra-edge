"""Seed a local threshold row for edge-only telemetry tests."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

load_dotenv(override=True)

from monitoring.infrastructure.threshold_repository import ThresholdRepository  # noqa: E402
from shared.infrastructure.database import init_db  # noqa: E402
from shared.infrastructure.database import db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", default="band-001")
    parser.add_argument("--heart-rate-min", type=int, default=60)
    parser.add_argument("--heart-rate-max", type=int, default=100)
    args = parser.parse_args()

    init_db()
    db.connect(reuse_if_open=True)
    try:
        changed = ThresholdRepository.upsert_from_cloud({
            "device_id": args.device_id,
            "heart_rate_min": args.heart_rate_min,
            "heart_rate_max": args.heart_rate_max,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        db.close()

    status = "created/updated" if changed else "already up to date"
    print(
        f"Threshold for {args.device_id} {status}: "
        f"{args.heart_rate_min}-{args.heart_rate_max} bpm"
    )


if __name__ == "__main__":
    main()
