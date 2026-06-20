"""Cloud registry synchronization gateway for the IAM bounded context.

Pulls the authoritative device registry from the cloud backend and applies it
to the local SQLite mirror.  The gateway authenticates as the edge server using
``GATEWAY_DEVICE_ID`` + ``GATEWAY_MAC_ADDRESS`` (``X-Device-Id`` / ``X-API-Key``).
"""
import logging
from datetime import datetime, timezone
from typing import Any

import requests
from dateutil.parser import parse as parse_datetime

from shared.infrastructure.config import EdgeConfig
from shared.infrastructure.gateway_auth import gateway_cloud_auth_headers

LOGGER = logging.getLogger(__name__)

REGISTRY_PATH = "/api/v1/edge/registry"


class CloudRegistryGateway:
    """Fetches device registry deltas from the cloud backend."""

    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = (base_url or EdgeConfig.API_SYNC_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else EdgeConfig.CLOUD_SYNC_TIMEOUT

    def pull(self, since: datetime | None) -> list[dict[str, Any]] | None:
        """Return registry entries updated after ``since``, or ``None`` on failure."""
        headers = gateway_cloud_auth_headers()
        if headers is None:
            LOGGER.warning(
                "Registry sync skipped: set GATEWAY_DEVICE_ID in .env (MAC is auto-detected)"
            )
            return None

        params = {}
        if since is not None:
            params["since"] = since.isoformat()

        url = f"{self.base_url}{REGISTRY_PATH}"
        try:
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            LOGGER.warning("Registry sync failed: %s", exc)
            return None

        if not response.ok:
            LOGGER.warning(
                "Registry sync rejected by cloud: %s %s",
                response.status_code,
                response.text,
            )
            return None

        payload = response.json()
        devices = payload.get("devices")
        if not isinstance(devices, list):
            LOGGER.warning("Registry sync response missing 'devices' array")
            return None

        return devices

    @staticmethod
    def parse_cloud_updated_at(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = parse_datetime(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError):
            return None
