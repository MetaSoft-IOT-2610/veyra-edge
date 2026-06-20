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
- ``NODE_SEED_PATH``: JSON file listing nodes to register on start-up.
- ``NODE_SEED_ENABLED``: toggle automatic node seeding (`true`/`false`).
- ``GATEWAY_DEVICE_ID``: stable identifier of this edge server at the cloud backend.
- ``GATEWAY_API_KEY``: secret API key paired with ``GATEWAY_DEVICE_ID`` for cloud auth.
- ``GATEWAY_DEVICE_TYPE``: device category for the edge gateway (default ``EDGE_GATEWAY``).
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
    NODE_SEED_PATH: str = _resolve_project_path(
        os.getenv("NODE_SEED_PATH", "nodes.seed.json"),
    )
    NODE_SEED_ENABLED: bool = os.getenv("NODE_SEED_ENABLED", "true").lower() == "true"
    GATEWAY_DEVICE_ID: str = os.getenv("GATEWAY_DEVICE_ID", "")
    GATEWAY_API_KEY: str = os.getenv("GATEWAY_API_KEY", "")
    GATEWAY_DEVICE_TYPE: str = os.getenv("GATEWAY_DEVICE_TYPE", "EDGE_GATEWAY")
