"""Application services for the Monitoring bounded context.

Application services sit between the interface layer and the domain layer.
They orchestrate use-cases by coordinating domain services, domain entities,
repositories and outbound gateways without containing domain logic themselves.
"""
import logging

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

    1. Cross-context validation – delegates to the IAM
       :class:`~iam.infrastructure.repositories.DeviceRepository` to verify the
       requesting device is registered and its API key is valid, and to obtain
       the tenant (``nursing_home_id``) the reading belongs to.
    2. Domain logic – delegates to
       :class:`~monitoring.domain.services.MeasurementService` to validate the
       raw vitals and build a :class:`~monitoring.domain.entities.Measurement`.
    3. Local buffering – persists the reading via
       :class:`~monitoring.infrastructure.repositories.MeasurementRepository`.
    4. Cloud synchronization – attempts to publish the reading through
       :class:`~monitoring.infrastructure.cloud_sync.MeasurementCloudGateway`;
       on failure the reading stays buffered (``synced = False``) for later
       retry.
    """

    def __init__(self):
        """Initialise the service with its required collaborators."""
        self.measurement_repository = MeasurementRepository()
        self.measurement_service = MeasurementService()
        self.device_repository = DeviceRepository()
        self.cloud_gateway = MeasurementCloudGateway()

    def create_measurement(
            self,
            mac_address: str,
            api_key: str,
            heart_rate=None,
            systolic=None,
            diastolic=None,
            temperature=None,
            oxygen_saturation=None,
            respiratory_rate=None,
            timestamp=None) -> Measurement:
        """Execute the *ingest measurement* use-case.

        Args:
            mac_address (str): Hardware MAC address of the submitting device.
            api_key (str): Value of the ``X-API-Key`` header used to authenticate.
            heart_rate, systolic, diastolic, temperature, oxygen_saturation,
            respiratory_rate: Optional raw vitals forwarded to the domain
                service for validation.
            timestamp (str | None): ISO 8601 timestamp of the reading.

        Returns:
            Measurement: The buffered measurement, with ``synced`` reflecting
            whether cloud publication succeeded.

        Raises:
            ValueError: If the device is unknown or the vitals are invalid.
        """
        # Cross-context guard: verify device identity via the IAM repository.
        device = self.device_repository.find_by_mac_and_api_key(mac_address, api_key)
        if not device:
            raise ValueError("Device not found")

        measurement = self.measurement_service.create_measurement(
            device, heart_rate, systolic, diastolic,
            temperature, oxygen_saturation, respiratory_rate, timestamp,
        )
        saved = self.measurement_repository.save(measurement)

        self._try_sync(saved)
        return saved

    def sync_pending(self) -> int:
        """Replay every buffered measurement that has not yet reached the cloud.

        Intended to be triggered periodically or after connectivity is restored.

        Returns:
            int: The number of measurements successfully synced in this run.
        """
        synced_count = 0
        for measurement in self.measurement_repository.find_unsynced():
            if self._try_sync(measurement):
                synced_count += 1
        return synced_count

    def _try_sync(self, measurement: Measurement) -> bool:
        """Attempt to publish a buffered measurement and flag it on success."""
        if not EdgeConfig.CLOUD_SYNC_ENABLED:
            return False
        published = self.cloud_gateway.publish(measurement)
        if published:
            self.measurement_repository.mark_as_synced(measurement.id)
            measurement.synced = True
        return published
