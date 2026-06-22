"""Application services for the Monitoring bounded context.

Application services sit between the interface layer and the domain layer.
They orchestrate use-cases by coordinating domain services, domain entities,
repositories and outbound gateways without containing domain logic themselves.
"""
import logging

from iam.application.registry_sync_service import DeviceRegistrySyncApplicationService
from iam.domain.entities import Device
from iam.infrastructure.repositories import DeviceRepository
from monitoring.domain.entities import Measurement
from monitoring.domain.services import MeasurementService
from monitoring.infrastructure.cloud_sync import MeasurementCloudGateway
from monitoring.infrastructure.repositories import MeasurementRepository
from shared.infrastructure.config import EdgeConfig

LOGGER = logging.getLogger(__name__)


class MeasurementApplicationService:
    """Application service that orchestrates the *ingest measurement* use-case.

    Responsibilities:

    1. Cross-context validation – the IAM :class:`~iam.domain.entities.Device`
       passed in was already authenticated at the interface layer.
    2. Domain logic – delegates to
       :class:`~monitoring.domain.services.MeasurementService` to validate vitals.
    3. Local buffering – persists via
       :class:`~monitoring.infrastructure.repositories.MeasurementRepository`.
    4. Cloud synchronization – publishes through
       :class:`~monitoring.infrastructure.cloud_sync.MeasurementCloudGateway`
       only when the node still exists as ``ACTIVE`` in the IAM registry
       (``device_id`` + ``mac_address``); the cloud backend applies the same
       check on ``deviceId`` + ``macAddress`` in the payload.
    """

    def __init__(self):
        """Initialise the service with its required collaborators."""
        self.measurement_repository = MeasurementRepository()
        self.device_repository = DeviceRepository()
        self.measurement_service = MeasurementService()
        self.cloud_gateway = MeasurementCloudGateway()
        self.registry_sync_service = DeviceRegistrySyncApplicationService()

    def create_measurement(
            self,
            device: Device,
            heart_rate=None,
            systolic=None,
            diastolic=None,
            temperature=None,
            oxygen_saturation=None,
            respiratory_rate=None,
            timestamp=None,
            ambient_temperature=None,
            latitude=None,
            longitude=None,
            satellite_count=None,
            satellites_in_view=None,
            diagnostics=None) -> Measurement:
        """Execute the *ingest measurement* use-case.

        Args:
            device (Device): Authenticated node from the IAM registry.
            heart_rate, systolic, diastolic, temperature, oxygen_saturation,
            respiratory_rate: Optional raw vitals from the embedded device.
            timestamp (str | None): ISO 8601 timestamp of the reading.

        Returns:
            Measurement: The buffered measurement, with ``synced`` reflecting
            whether cloud publication succeeded.

        Raises:
            ValueError: If the vitals are invalid.
        """
        measurement = self.measurement_service.create_measurement(
            device.device_id,
            device.device_type,
            heart_rate,
            systolic,
            diastolic,
            temperature,
            oxygen_saturation,
            respiratory_rate,
            ambient_temperature,
            latitude,
            longitude,
            satellite_count,
            satellites_in_view,
            timestamp,
            diagnostics,
        )
        saved = self.measurement_repository.save(measurement)

        self._try_sync(saved, sync_registry=True)
        return saved

    def sync_pending(self, limit: int | None = None) -> int:
        """Replay unsynced measurements up to ``limit`` (defaults to config batch size)."""
        batch_size = limit if limit is not None else EdgeConfig.CLOUD_SYNC_BATCH_SIZE
        if batch_size <= 0:
            return 0

        synced_count = 0
        for measurement in self.measurement_repository.find_unsynced(limit=batch_size):
            if self._try_sync(measurement, sync_registry=False):
                synced_count += 1
        if synced_count:
            self._sync_registry_from_cloud()

        remaining = self.measurement_repository.count_unsynced()
        if remaining:
            LOGGER.info(
                "Cloud sync batch complete: synced=%s, remaining unsynced=%s (batch_size=%s)",
                synced_count,
                remaining,
                batch_size,
            )
        return synced_count

    def _try_sync(self, measurement: Measurement, sync_registry: bool = True) -> bool:
        """Attempt to publish a buffered measurement and flag it on success."""
        if not EdgeConfig.CLOUD_SYNC_ENABLED:
            return False

        device = self.device_repository.find_by_device_id(measurement.device_id)
        if not device:
            LOGGER.warning(
                "Cloud sync skipped for device %s: not in ACTIVE registry",
                measurement.device_id,
            )
            return False

        published = self.cloud_gateway.publish(measurement, device.mac_address)
        if published:
            self.measurement_repository.mark_as_synced(measurement.id)
            measurement.synced = True
            if sync_registry:
                self._sync_registry_from_cloud()
        return published

    def _sync_registry_from_cloud(self) -> None:
        if not EdgeConfig.REGISTRY_SYNC_ENABLED:
            return
        try:
            self.registry_sync_service.sync_from_cloud()
        except Exception as exc:
            LOGGER.warning("Registry sync after cloud publish failed: %s", exc)
