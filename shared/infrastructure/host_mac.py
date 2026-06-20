"""Resolve the host network MAC address for edge gateway cloud authentication."""
from __future__ import annotations

import logging
import platform
import re
import subprocess
import uuid

LOGGER = logging.getLogger(__name__)

_MAC_WITH_SEPARATORS = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")
_DETECTED_MAC: str | None = None
_DETECTION_ATTEMPTED = False


def normalize_mac_address(mac: str) -> str:
    """Normalize a MAC to uppercase ``AA:BB:CC:DD:EE:FF`` form."""
    if not mac or not str(mac).strip():
        raise ValueError("mac_address cannot be empty")

    cleaned = str(mac).strip().upper().replace("-", ":")
    if ":" not in cleaned and len(cleaned) == 12 and re.fullmatch(r"[0-9A-F]{12}", cleaned):
        cleaned = ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))

    if not _MAC_WITH_SEPARATORS.fullmatch(cleaned):
        raise ValueError("mac_address must be a valid MAC address")

    return cleaned


def detect_host_mac_address() -> str | None:
    """Return the MAC of the primary active network interface, if detectable."""
    system = platform.system()
    if system == "Windows":
        mac = _detect_windows_mac()
    elif system == "Linux":
        mac = _detect_linux_mac()
    elif system == "Darwin":
        mac = _detect_darwin_mac()
    else:
        mac = None

    if mac:
        return mac
    return _detect_from_uuid_node()


def _detect_windows_mac() -> str | None:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.MacAddress } "
                "| Sort-Object -Property InterfaceMetric | Select-Object -First 1).MacAddress",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        mac = result.stdout.strip()
        if mac:
            return normalize_mac_address(mac)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        LOGGER.debug("Windows MAC detection failed: %s", exc)
    return None


def _detect_linux_mac() -> str | None:
    iface = _linux_default_interface()
    if not iface:
        return None
    address_path = f"/sys/class/net/{iface}/address"
    try:
        with open(address_path, encoding="utf-8") as handle:
            return normalize_mac_address(handle.read().strip())
    except (OSError, ValueError) as exc:
        LOGGER.debug("Linux MAC detection failed for %s: %s", iface, exc)
        return None


def _linux_default_interface() -> str | None:
    try:
        with open("/proc/net/route", encoding="utf-8") as handle:
            for line in handle.readlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "00000000":
                    return parts[0]
    except OSError:
        return None
    return None


def _detect_darwin_mac() -> str | None:
    try:
        route = subprocess.run(
            ["route", "-n", "get", "default"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        iface = None
        for line in route.stdout.splitlines():
            if line.strip().startswith("interface:"):
                iface = line.split(":", 1)[1].strip()
                break
        if not iface:
            return None
        result = subprocess.run(
            ["ifconfig", iface],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        match = re.search(r"ether\s+([0-9a-f:]+)", result.stdout, re.IGNORECASE)
        if match:
            return normalize_mac_address(match.group(1))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        LOGGER.debug("macOS MAC detection failed: %s", exc)
    return None


def _detect_from_uuid_node() -> str | None:
    node = uuid.getnode()
    if (node >> 40) & 1:
        return None
    raw = node.to_bytes(6, "big")
    return normalize_mac_address(":".join(f"{byte:02X}" for byte in raw))


def resolve_gateway_mac_address(env_override: str = "") -> str | None:
    """Use ``GATEWAY_MAC_ADDRESS`` when set; otherwise detect at runtime."""
    global _DETECTED_MAC, _DETECTION_ATTEMPTED

    if _DETECTION_ATTEMPTED:
        return _DETECTED_MAC

    _DETECTION_ATTEMPTED = True
    override = (env_override or "").strip()
    if override:
        try:
            _DETECTED_MAC = normalize_mac_address(override)
            LOGGER.info("Gateway cloud auth uses MAC from GATEWAY_MAC_ADDRESS: %s", _DETECTED_MAC)
            return _DETECTED_MAC
        except ValueError as exc:
            LOGGER.error("Invalid GATEWAY_MAC_ADDRESS override: %s", exc)
            return None

    _DETECTED_MAC = detect_host_mac_address()
    if _DETECTED_MAC:
        LOGGER.info("Gateway cloud auth uses runtime host MAC: %s", _DETECTED_MAC)
    else:
        LOGGER.warning(
            "Could not resolve gateway MAC address; set GATEWAY_MAC_ADDRESS in .env as override"
        )
    return _DETECTED_MAC
