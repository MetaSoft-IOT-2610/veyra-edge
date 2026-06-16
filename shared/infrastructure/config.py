"""Centralized runtime configuration for the Veyra Edge Service.

Reads configuration from environment variables (optionally loaded from a
``.env`` file during application start-up) so the service behaves identically
across local development and on-premise edge deployments without code changes.

The variables mirror the deployment contract documented for the Edge Server:

- ``SQLITE_DB_PATH``: local path of the SQLite database used for offline
  buffering of telemetry.
- ``API_SYNC_URL``: base URL of the cloud backend used to publish telemetry.
- ``EDGE_DEVICE_PORT``: serial/network port of the IoT device (reserved for
  future device-ingestion transports).
- ``CLOUD_SYNC_ENABLED``: feature flag to toggle cloud synchronization.
- ``CLOUD_SYNC_TIMEOUT``: HTTP timeout (seconds) for cloud sync requests.
"""
import os


class EdgeConfig:
    """Immutable view over the edge-service runtime configuration.

    Values are resolved once, at import time, from the process environment.
    Defaults are chosen so the service starts successfully in a local
    development environment with no ``.env`` file present.
    """

    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "veyra_edge.db")
    API_SYNC_URL: str = os.getenv("API_SYNC_URL", "http://localhost:8080")
    EDGE_DEVICE_PORT: str = os.getenv("EDGE_DEVICE_PORT", "")
    CLOUD_SYNC_ENABLED: bool = os.getenv("CLOUD_SYNC_ENABLED", "true").lower() == "true"
    CLOUD_SYNC_TIMEOUT: float = float(os.getenv("CLOUD_SYNC_TIMEOUT", "5"))
