"""Periodic cloud registry synchronization for the edge runtime."""
import logging
import time

from iam.application.registry_sync_service import DeviceRegistrySyncApplicationService
from monitoring.application.services import MeasurementApplicationService
from monitoring.application.threshold_sync_service import ThresholdSyncApplicationService
from shared.infrastructure.config import EdgeConfig

LOGGER = logging.getLogger(__name__)

_last_registry_sync_monotonic = 0.0
_last_pending_sync_monotonic = 0.0
_last_threshold_sync_monotonic = 0.0
PENDING_SYNC_INTERVAL_SECONDS = 60.0


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


def maybe_sync_pending_measurements() -> None:
    """Retry unsynced measurements when cloud connectivity returns."""
    global _last_pending_sync_monotonic

    if not EdgeConfig.CLOUD_SYNC_ENABLED:
        return

    now = time.monotonic()
    if now - _last_pending_sync_monotonic < PENDING_SYNC_INTERVAL_SECONDS:
        return

    _last_pending_sync_monotonic = now
    try:
        synced = MeasurementApplicationService().sync_pending()
        if synced:
            LOGGER.info(
                "Replayed %s pending measurement(s) to cloud (batch_size=%s)",
                synced,
                EdgeConfig.CLOUD_SYNC_BATCH_SIZE,
            )
    except Exception as exc:
        LOGGER.warning("Pending measurement sync failed: %s", exc)


def maybe_sync_thresholds_from_cloud() -> None:
    """Pull threshold deltas from the cloud when the configured interval elapses."""
    global _last_threshold_sync_monotonic

    if not EdgeConfig.THRESHOLD_SYNC_ENABLED:
        return

    now = time.monotonic()
    if now - _last_threshold_sync_monotonic < EdgeConfig.THRESHOLD_SYNC_INTERVAL_SECONDS:
        return

    _last_threshold_sync_monotonic = now
    try:
        ThresholdSyncApplicationService().sync_from_cloud()
    except Exception as exc:
        LOGGER.warning("Background threshold sync failed: %s", exc)


def sync_thresholds_from_cloud_on_startup() -> int:
    """Run an eager threshold sync during application bootstrap."""
    if not EdgeConfig.THRESHOLD_SYNC_ENABLED:
        return 0
    return ThresholdSyncApplicationService().sync_from_cloud()


def sync_thresholds_on_request() -> int:
    """Pull threshold deltas from the cloud immediately, ignoring the scheduler interval.

    Unlike :func:`maybe_sync_thresholds_from_cloud`, this helper does not
    consult ``THRESHOLD_SYNC_INTERVAL_SECONDS`` and runs on every invocation.
    It is intended to be called from per-request hot paths (for example, on
    every incoming telemetry request) so the local threshold cache reflects
    the latest cloud configuration as soon as a device reports vitals.

    The function honours ``THRESHOLD_SYNC_ENABLED`` and swallows transport
    errors so that callers on the request path are not affected by transient
    cloud unavailability.

    Returns:
        int: Number of threshold records created or updated.  ``0`` when
        threshold sync is disabled or when the cloud sync raised an error.
    """
    if not EdgeConfig.THRESHOLD_SYNC_ENABLED:
        return 0
    try:
        return ThresholdSyncApplicationService().sync_from_cloud()
    except Exception as exc:
        LOGGER.warning("On-request threshold sync failed: %s", exc)
        return 0
