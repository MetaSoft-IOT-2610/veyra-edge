"""Gateway authentication headers for edge → cloud HTTP calls.

Uses the same header names as smart-band node → edge (``X-Device-Id`` +
``X-API-Key``). The credential in ``X-API-Key`` is the gateway MAC address,
read from the host network interface at runtime (like ``WiFi.macAddress()`` on
the ESP32). Set ``GATEWAY_MAC_ADDRESS`` in ``.env`` only to override detection.
"""
from shared.infrastructure.config import EdgeConfig
from shared.infrastructure.host_mac import resolve_gateway_mac_address


def gateway_cloud_auth_headers() -> dict[str, str] | None:
    """Return gateway auth headers, or ``None`` when credentials are missing."""
    device_id = EdgeConfig.GATEWAY_DEVICE_ID.strip()
    mac_address = resolve_gateway_mac_address(EdgeConfig.GATEWAY_MAC_ADDRESS)
    if not device_id or not mac_address:
        return None
    return {
        "X-Device-Id": device_id,
        "X-API-Key": mac_address,
    }
