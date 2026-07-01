"""Application services for the Monitoring bounded context.

Application services sit between the interface layer and the domain layer.
They orchestrate use-cases by coordinating domain services, domain entities,
repositories and outbound gateways without containing domain logic themselves.
"""
import logging
import time

from iam.application.registry_sync_service import DeviceRegistrySyncApplicationService
from iam.domain.entities import Device
from iam.infrastructure.repositories import DeviceRepository
from monitoring.application.threshold_sync_service import ThresholdSyncApplicationService
from monitoring.domain.entities import Measurement
from monitoring.domain.services import MeasurementService
from monitoring.infrastructure.cloud_sync import MeasurementCloudGateway
from monitoring.infrastructure.repositories import MeasurementRepository
from monitoring.infrastructure.threshold_repository import ThresholdRepository
from shared.infrastructure.config import EdgeConfig

LOGGER = logging.getLogger(__name__)


class HeartRateAverageWindow:
    """In-memory pulse averaging window for one vital-signs device."""

    def __init__(self, measurement: Measurement, now_monotonic: float, threshold_checked: bool):
        self.device_id = measurement.device_id
        self.device_type = measurement.device_type
        self.started_at_monotonic = now_monotonic
        self.latest_timestamp = measurement.timestamp
        self.threshold_checked = threshold_checked
        self.total = 0
        self.count = 0
        self.add(measurement)

    def add(self, measurement: Measurement) -> None:
        self.total += measurement.heart_rate
        self.count += 1
        self.latest_timestamp = measurement.timestamp

    def is_ready(self, now_monotonic: float, window_seconds: int) -> bool:
        return now_monotonic - self.started_at_monotonic >= window_seconds

    def to_average_measurement(self) -> Measurement:
        return Measurement(
            device_id=self.device_id,
            device_type=self.device_type,
            timestamp=self.latest_timestamp,
            heart_rate=round(self.total / self.count),
        )


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
        self.threshold_sync_service = ThresholdSyncApplicationService()
        self.threshold_repository = ThresholdRepository()
        self.heart_rate_windows = {}
        self.last_thresholds_applied = 0

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
        self.last_thresholds_applied = self._sync_thresholds_from_cloud()

        threshold = self.threshold_repository.find_by_device_id(measurement.device_id)

        if self._should_publish_immediately(measurement, threshold):
            self.heart_rate_windows.pop(measurement.device_id, None)
            return self._save_and_sync(measurement, immediate_alert=True)

        averaged = self._try_create_heart_rate_average(measurement, threshold_checked=threshold is not None)
        if averaged is None:
            measurement.synced = False
            measurement.average_pending = True
            measurement.averaged = False
            measurement.immediate_alert = False
            return measurement

        return self._save_and_sync(averaged, averaged=True)

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

    def _save_and_sync(
            self,
            measurement: Measurement,
            *,
            averaged: bool = False,
            immediate_alert: bool = False) -> Measurement:
        """Persist a publishable measurement and attempt cloud synchronization."""
        saved = self.measurement_repository.save(measurement)
        self._try_sync(saved, sync_registry=True)
        saved.average_pending = False
        saved.averaged = averaged
        saved.immediate_alert = immediate_alert
        return saved

    def _should_publish_immediately(self, measurement: Measurement, threshold) -> bool:
        """Return true when the reading must bypass averaging."""
        if measurement.heart_rate is None:
            return True

        if threshold is None:
            return False

        if threshold.heart_rate_min is not None and measurement.heart_rate < threshold.heart_rate_min:
            return True
        return threshold.heart_rate_max is not None and measurement.heart_rate > threshold.heart_rate_max

    def _try_create_heart_rate_average(
            self,
            measurement: Measurement,
            *,
            threshold_checked: bool) -> Measurement | None:
        """Accumulate normal pulse readings and emit an average when the window matures."""
        window_seconds = EdgeConfig.HEART_RATE_AVERAGE_WINDOW_SECONDS
        if window_seconds <= 0:
            return measurement

        now = time.monotonic()
        window = self.heart_rate_windows.get(measurement.device_id)
        if window is None or window.threshold_checked != threshold_checked:
            self.heart_rate_windows[measurement.device_id] = HeartRateAverageWindow(
                measurement,
                now,
                threshold_checked,
            )
            return None

        window.add(measurement)
        if not window.is_ready(now, window_seconds):
            return None

        averaged = window.to_average_measurement()
        self.heart_rate_windows.pop(measurement.device_id, None)
        return averaged

    def _sync_registry_from_cloud(self) -> None:
        if not EdgeConfig.REGISTRY_SYNC_ENABLED:
            return
        try:
            self.registry_sync_service.sync_from_cloud()
        except Exception as exc:
            LOGGER.warning("Registry sync after cloud publish failed: %s", exc)

    def _sync_thresholds_from_cloud(self) -> int:
        """Pull threshold deltas from the cloud after ingesting a telemetry reading.

        This hook is invoked on every successful call to
        :meth:`create_measurement` so the edge keeps the locally cached
        thresholds aligned with the cloud configuration on each telemetry
        request, rather than only on the time-based scheduler.

        Returns:
            int: Number of threshold records created or updated during this
            call.  ``0`` when ``THRESHOLD_SYNC_ENABLED`` is disabled, when the
            cloud is unreachable, or when the cloud returned no deltas.
        """
        if not EdgeConfig.THRESHOLD_SYNC_ENABLED:
            return 0
        try:
            return self.threshold_sync_service.sync_from_cloud()
        except Exception as exc:
            LOGGER.warning("Threshold sync after telemetry ingest failed: %s", exc)
            return 0
