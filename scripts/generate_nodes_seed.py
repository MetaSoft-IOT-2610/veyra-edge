#!/usr/bin/env python3
"""Generate nodes.seed.json for local development.

Aligns with veyra-embedded-app secrets.h (default device_id band-001).
The MAC must match WiFi.macAddress() printed by the ESP32 at boot.

Examples:
    py scripts/generate_nodes_seed.py --mac 24:6F:28:AB:CD:EF
    py scripts/generate_nodes_seed.py --port COM4
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "nodes.seed.json"
MAC_PATTERN = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


def normalize_mac(mac: str) -> str:
    cleaned = mac.strip().upper().replace("-", ":")
    if ":" not in cleaned and len(cleaned) == 12:
        cleaned = ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    if not MAC_PATTERN.fullmatch(cleaned):
        raise ValueError(f"Invalid MAC address: {mac!r}")
    return cleaned


def read_mac_from_esptool(port: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "esptool", "--port", port, "read-mac"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"MAC:\s*([0-9a-f:]+)", output, re.IGNORECASE)
    if not match:
        raise RuntimeError(
            f"Could not read MAC from {port}. Close the Arduino Serial Monitor and retry.\n{output.strip()}"
        )
    return normalize_mac(match.group(1))


def build_payload(device_id: str, mac_address: str, device_type: str) -> dict:
    return {
        "nodes": [
            {
                "device_id": device_id,
                "mac_address": mac_address,
                "device_type": device_type,
            }
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate nodes.seed.json for dev.")
    parser.add_argument("--device-id", default="band-001", help="Node id (secrets.h DEVICE_ID)")
    parser.add_argument("--device-type", default="VITAL_SIGNS", choices=["VITAL_SIGNS", "GPS"])
    parser.add_argument("--mac", help="ESP32 Wi-Fi MAC (WiFi.macAddress() from Serial)")
    parser.add_argument("--port", help="Serial port for esptool read-mac (e.g. COM4)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    mac = args.mac
    if mac:
        mac = normalize_mac(mac)
    elif args.port:
        mac = read_mac_from_esptool(args.port)
    else:
        parser.error("Provide --mac or --port (close Serial Monitor before using --port)")

    payload = build_payload(args.device_id, mac, args.device_type)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"  device_id:   {args.device_id}")
    print(f"  mac_address: {mac}")
    print(f"  device_type: {args.device_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
