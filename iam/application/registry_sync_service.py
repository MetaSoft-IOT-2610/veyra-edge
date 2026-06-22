"""Application service that synchronizes the local IAM registry from the cloud."""
import logging

from iam.infrastructure.registry_sync import CloudRegistryGateway
from iam.infrastructure.repositories import DeviceRepository
from shared.infrastructure.config import EdgeConfig

LOGGER = logging.getLogger(__name__)


class DeviceRegistrySyncApplicationService:
    """Pulls the cloud device registry and upserts the local SQLite mirror."""

    def __init__(self):
        self.device_repository = DeviceRepository()
        self.registry_gateway = CloudRegistryGateway()

    def sync_from_cloud(self) -> int:
        """Fetch registry deltas from the cloud and apply them locally.

        Returns:
            int: Number of device records created or updated.  ``0`` when sync
            is disabled, credentials are missing, or the cloud is unreachable.
        """
        if not EdgeConfig.REGISTRY_SYNC_ENABLED:
            return 0

        since = self.device_repository.get_max_cloud_updated_at()
        entries = self.registry_gateway.pull(since)
        if entries is None:
            LOGGER.warning("Registry sync failed: cloud rejected or unreachable (check GATEWAY_DEVICE_ID + MAC in cloud)")
            return 0

        applied = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                if self.device_repository.upsert_from_cloud(entry):
                    applied += 1
            except ValueError as exc:
                LOGGER.warning("Skipping invalid registry entry: %s", exc)

        if applied:
            LOGGER.info("Registry sync applied %s device record(s) from cloud", applied)
        elif entries:
            LOGGER.info("Registry sync complete: %s device(s) already up to date", len(entries))
        else:
            LOGGER.info("Registry sync complete: cloud registry is empty or unreachable")
        return applied
