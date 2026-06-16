"""Repository implementation for the Monitoring bounded context.

Maps between the :class:`~monitoring.domain.entities.Measurement` domain entity
and the :class:`~monitoring.infrastructure.models.Measurement` Peewee ORM model,
shielding the application layer from persistence details.
"""
from datetime import datetime, timezone
from typing import List

from monitoring.domain.entities import Measurement
from monitoring.infrastructure.models import Measurement as MeasurementModel


class MeasurementRepository:
    """Repository that persists and reconstructs :class:`~monitoring.domain.entities.Measurement` entities."""

    @staticmethod
    def _to_entity(model: MeasurementModel) -> Measurement:
        """Map a Peewee ``Measurement`` row to a domain :class:`Measurement` entity."""
        return Measurement(
            device_id=model.device_id,
            mac_address=model.mac_address,
            nursing_home_id=model.nursing_home_id,
            timestamp=model.timestamp,
            heart_rate=model.heart_rate,
            systolic=model.systolic,
            diastolic=model.diastolic,
            temperature=model.temperature,
            oxygen_saturation=model.oxygen_saturation,
            respiratory_rate=model.respiratory_rate,
            synced=model.synced,
            id=model.id,
        )

    def save(self, measurement: Measurement) -> Measurement:
        """Persist a transient measurement into the local buffer.

        Args:
            measurement (Measurement): The transient entity to persist.

        Returns:
            Measurement: A copy enriched with the database-assigned ``id``.
        """
        model = MeasurementModel.create(
            device_id=measurement.device_id,
            mac_address=measurement.mac_address,
            nursing_home_id=measurement.nursing_home_id,
            timestamp=measurement.timestamp,
            heart_rate=measurement.heart_rate,
            systolic=measurement.systolic,
            diastolic=measurement.diastolic,
            temperature=measurement.temperature,
            oxygen_saturation=measurement.oxygen_saturation,
            respiratory_rate=measurement.respiratory_rate,
            synced=measurement.synced,
            created_at=datetime.now(timezone.utc),
        )
        return self._to_entity(model)

    def mark_as_synced(self, measurement_id: int) -> None:
        """Flag a buffered measurement as successfully published to the cloud.

        Args:
            measurement_id (int): Identity of the measurement to update.
        """
        (MeasurementModel
         .update(synced=True)
         .where(MeasurementModel.id == measurement_id)
         .execute())

    def find_unsynced(self) -> List[Measurement]:
        """Return all buffered measurements not yet published to the cloud.

        Ordered by ``id`` so they are replayed in capture order.
        """
        query = (MeasurementModel
                 .select()
                 .where(MeasurementModel.synced == False)  # noqa: E712 (peewee needs ==)
                 .order_by(MeasurementModel.id))
        return [self._to_entity(model) for model in query]
