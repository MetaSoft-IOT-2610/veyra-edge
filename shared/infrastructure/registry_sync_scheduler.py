"""Periodic cloud registry synchronization for the edge runtime."""
import logging
import time

from iam.application.registry_sync_service import DeviceRegistrySyncApplicationService
from shared.infrastructure.config import EdgeConfig

LOGGER = logging.getLogger(__name__)

_last_registry_sync_monotonic = 0.0


def maybe_sync_registry_from_cloud() -> None:
    """Pull registry deltas from the cloud when the configured interval elapses."""
    global _last_registry_sync_monotonic

    if not EdgeConfig.REGISTRY_SYNC_ENABLED:
        return

    now = time.monotonic()
    if now - _last_registry_sync_monotonic < EdgeConfig.REGISTRY_SYNC_INTERVAL_SECONDS:
        return

    _last_registry_sync_monotonic = now
    try:
        DeviceRegistrySyncApplicationService().sync_from_cloud()
    except Exception as exc:
        LOGGER.warning("Background registry sync failed: %s", exc)


def sync_registry_from_cloud_on_startup() -> int:
    """Run an eager registry sync during application bootstrap."""
    if not EdgeConfig.REGISTRY_SYNC_ENABLED:
        return 0
    return DeviceRegistrySyncApplicationService().sync_from_cloud()
