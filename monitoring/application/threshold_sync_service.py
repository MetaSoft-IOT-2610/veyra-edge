"""Application service that synchronizes vital-sign thresholds from the cloud."""
import logging

from monitoring.infrastructure.threshold_cloud_sync import ThresholdCloudGateway
from monitoring.infrastructure.threshold_repository import ThresholdRepository
from shared.infrastructure.config import EdgeConfig

LOGGER = logging.getLogger(__name__)


class ThresholdSyncApplicationService:
    """Pulls cloud threshold configurations and upserts the local SQLite mirror."""

    def __init__(self):
        self.threshold_repository = ThresholdRepository()
        self.threshold_gateway = ThresholdCloudGateway()

    def sync_from_cloud(self) -> int:
        """Fetch threshold deltas from the cloud and apply them locally.

        Returns:
            int: Number of threshold records created or updated.  ``0`` when sync
            is disabled, credentials are missing, or the cloud is unreachable.
        """
        if not EdgeConfig.THRESHOLD_SYNC_ENABLED:
            return 0

        since = self.threshold_repository.get_max_cloud_updated_at()
        entries = self.threshold_gateway.pull(since)
        if entries is None:
            LOGGER.warning(
                "Threshold sync failed: cloud rejected or unreachable "
                "(check GATEWAY_DEVICE_ID + MAC in cloud)"
            )
            return 0

        applied = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                if self.threshold_repository.upsert_from_cloud(entry):
                    applied += 1
            except (ValueError, KeyError) as exc:
                LOGGER.warning("Skipping invalid threshold entry: %s", exc)

        if applied:
            LOGGER.info("Threshold sync applied %s record(s) from cloud", applied)
        elif entries:
            LOGGER.info("Threshold sync complete: %s record(s) already up to date", len(entries))
        else:
            LOGGER.info("Threshold sync complete: cloud returned no threshold records")
        return applied
