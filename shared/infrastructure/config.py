"""Centralized runtime configuration for the Veyra Edge Service.

Reads configuration from environment variables (optionally loaded from a
``.env`` file during application start-up) so the service behaves identically
across local development and on-premise edge deployments without code changes.

The variables mirror the deployment contract documented for the Edge Server:

- ``SQLITE_DB_PATH``: local path of the SQLite database used for offline
  buffering of telemetry.
- ``API_SYNC_URL``: cloud backend API base URL including ``/api/v1`` (e.g.
  ``https://host.example.com/api/v1``).  Relative paths such as ``/measurements``
  are appended by the edge gateways.
- ``EDGE_DEVICE_PORT``: serial/network port of the IoT device (reserved for
  future device-ingestion transports).
- ``CLOUD_SYNC_ENABLED``: feature flag to toggle cloud synchronization.
- ``CLOUD_SYNC_TIMEOUT``: HTTP timeout (seconds) for cloud sync requests.
- ``CLOUD_SYNC_BATCH_SIZE``: max unsynced measurements replayed per background cycle.
- ``NODE_SEED_PATH``: JSON file listing nodes to register on start-up.
- ``NODE_SEED_ENABLED``: toggle automatic node seeding (`true`/`false`).
- ``GATEWAY_DEVICE_ID``: stable identifier of this edge server at the cloud backend.
- ``GATEWAY_MAC_ADDRESS``: optional override for the gateway MAC sent in ``X-Device-Mac``.
  When empty, the edge reads the primary host network interface MAC at runtime.
- ``GATEWAY_DEVICE_TYPE``: device category for the edge gateway (default ``EDGE_GATEWAY``).
- ``EDGE_JWT_SECRET``: signing secret for edge-issued device access tokens.
- ``EDGE_JWT_TTL_SECONDS``: lifetime (seconds) of device access tokens after sign-in.
- ``REGISTRY_SYNC_ENABLED``: pull the device registry from the cloud (source of truth).
- ``REGISTRY_SYNC_INTERVAL_SECONDS``: interval between background registry sync polls.
"""
import os

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _resolve_project_path(path: str) -> str:
    """Resolve a config path relative to the project root when not absolute."""
    if os.path.isabs(path):
        return path
    return os.path.join(_PROJECT_ROOT, path)


class EdgeConfig:
    """Immutable view over the edge-service runtime configuration.

    Values are resolved once, at import time, from the process environment.
    Defaults are chosen so the service starts successfully in a local
    development environment with no ``.env`` file present.
    """

    SQLITE_DB_PATH: str = _resolve_project_path(
        os.getenv("SQLITE_DB_PATH", "veyra_edge.db"),
    )
    API_SYNC_URL: str = os.getenv("API_SYNC_URL", "http://localhost:8080")
    EDGE_DEVICE_PORT: str = os.getenv("EDGE_DEVICE_PORT", "")
    CLOUD_SYNC_ENABLED: bool = os.getenv("CLOUD_SYNC_ENABLED", "true").lower() == "true"
    CLOUD_SYNC_TIMEOUT: float = float(os.getenv("CLOUD_SYNC_TIMEOUT", "5"))
    CLOUD_SYNC_BATCH_SIZE: int = int(os.getenv("CLOUD_SYNC_BATCH_SIZE", "20"))
    NODE_SEED_PATH: str = _resolve_project_path(
        os.getenv("NODE_SEED_PATH", "nodes.seed.json"),
    )
    NODE_SEED_ENABLED: bool = os.getenv("NODE_SEED_ENABLED", "true").lower() == "true"
    GATEWAY_DEVICE_ID: str = os.getenv("GATEWAY_DEVICE_ID", "")
    GATEWAY_MAC_ADDRESS: str = os.getenv("GATEWAY_MAC_ADDRESS", "")
    GATEWAY_DEVICE_TYPE: str = os.getenv("GATEWAY_DEVICE_TYPE", "EDGE_GATEWAY")
    EDGE_JWT_SECRET: str = os.getenv("EDGE_JWT_SECRET", "")
    EDGE_JWT_TTL_SECONDS: int = int(os.getenv("EDGE_JWT_TTL_SECONDS", "3600"))
    REGISTRY_SYNC_ENABLED: bool = os.getenv("REGISTRY_SYNC_ENABLED", "false").lower() == "true"
    REGISTRY_SYNC_INTERVAL_SECONDS: int = int(os.getenv("REGISTRY_SYNC_INTERVAL_SECONDS", "300"))
