"""Exercise the local pulse telemetry flow without embedded hardware.

Prerequisites:
  1. Copy .env.example.local-test to .env.
  2. Start the edge service: python app.py
  3. Run this script from the repo root:
       python scripts/test_pulse_flow.py

The script signs in as the seeded band-001 device and sends:
  - one normal pulse reading, expected to be held for averaging
  - a second normal pulse after the averaging window, expected to publish the average
  - one abnormal pulse, expected to bypass averaging immediately
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import requests


DEFAULT_EDGE_URL = "http://localhost:5000"
DEFAULT_DEVICE_ID = "band-001"
DEFAULT_MAC_ADDRESS = "AA:BB:CC:DD:EE:FF"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def print_response(label: str, response: requests.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    print(f"\n{label} -> HTTP {response.status_code}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    response.raise_for_status()
    return payload


def sign_in(base_url: str, device_id: str, mac_address: str) -> str:
    response = requests.post(
        f"{base_url}/api/v1/auth/sign-in",
        headers={
            "X-Device-Id": device_id,
            "X-Device-Mac": mac_address,
        },
        timeout=5,
    )
    payload = print_response("sign-in", response)
    return payload["access_token"]


def send_pulse(base_url: str, token: str, heart_rate: int) -> dict:
    response = requests.post(
        f"{base_url}/api/v1/monitoring/data-records",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "heart_rate": heart_rate,
            "timestamp": iso_now(),
        },
        timeout=5,
    )
    return print_response(f"pulse {heart_rate}", response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edge-url", default=DEFAULT_EDGE_URL)
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID)
    parser.add_argument("--mac-address", default=DEFAULT_MAC_ADDRESS)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--normal-a", type=int, default=80)
    parser.add_argument("--normal-b", type=int, default=90)
    parser.add_argument("--abnormal", type=int, default=130)
    args = parser.parse_args()

    token = sign_in(args.edge_url, args.device_id, args.mac_address)

    first = send_pulse(args.edge_url, token, args.normal_a)
    print("\nExpected: average_pending=true for first normal reading.")
    if not first.get("average_pending"):
        print("Warning: first reading was not held for averaging.")

    wait_seconds = max(1, args.window_seconds + 1)
    print(f"\nWaiting {wait_seconds}s so the average window can mature...")
    time.sleep(wait_seconds)

    second = send_pulse(args.edge_url, token, args.normal_b)
    print("\nExpected: averaged=true for second normal reading.")
    if not second.get("averaged"):
        print("Warning: second reading did not publish an average.")

    abnormal = send_pulse(args.edge_url, token, args.abnormal)
    print("\nExpected: immediate_alert=true when local thresholds are cached.")
    if not abnormal.get("immediate_alert"):
        print("Warning: abnormal reading was not marked as an immediate alert.")


if __name__ == "__main__":
    main()
