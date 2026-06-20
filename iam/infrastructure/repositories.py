"""Repository implementation for the IAM bounded context.

Provides the persistence adapter that maps between the
:class:`~iam.domain.entities.Device` domain entity and the
:class:`~iam.infrastructure.models.Device` Peewee ORM model.

Following the Repository pattern, callers in the application layer work only
with domain entities and remain isolated from ORM and database details.
"""
from typing import List, Optional

import peewee

from iam.domain.entities import Device
from iam.domain.exceptions import DeviceAlreadyExistsError
from iam.infrastructure.models import Device as DeviceModel


class DeviceRepository:
    """Repository that persists and reconstructs :class:`~iam.domain.entities.Device` entities.

    All ORM-to-entity mapping is contained within this class, ensuring the
    domain layer has no dependency on Peewee.
    """

    @staticmethod
    def _to_entity(model: DeviceModel) -> Device:
        """Map a Peewee ``Device`` row to a domain :class:`Device` entity."""
        return Device(
            device_id=model.device_id,
            device_type=model.device_type,
            api_key=model.api_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
            id=model.id,
        )

    @staticmethod
    def save(device: Device) -> Device:
        """Persist a new device provisioned by the backend.

        Args:
            device (Device): The transient entity to persist.

        Returns:
            Device: The persisted entity enriched with its assigned ``id``.

        Raises:
            DeviceAlreadyExistsError: If a device with the same ``device_id``
                already exists.
        """
        try:
            model = DeviceModel.create(
                device_id=device.device_id,
                device_type=device.device_type,
                api_key=device.api_key,
                created_at=device.created_at,
                updated_at=device.updated_at,
            )
        except peewee.IntegrityError:
            raise DeviceAlreadyExistsError(
                f"Device already exists for device_id '{device.device_id}'"
            )
        return DeviceRepository._to_entity(model)

    @staticmethod
    def find_by_device_id(device_id: str) -> Optional[Device]:
        """Look up a device by its stable node identifier."""
        try:
            model = DeviceModel.get(DeviceModel.device_id == device_id)
            return DeviceRepository._to_entity(model)
        except peewee.DoesNotExist:
            return None

    @staticmethod
    def find_by_id_and_api_key(device_id: str, api_key: str) -> Optional[Device]:
        """Look up a device by its node identifier and API key.

        Used to authenticate inbound telemetry.  Returns ``None`` (rather than
        raising) when no match is found, letting the domain service apply the
        authentication rule without catching infrastructure exceptions.

        Args:
            device_id (str): The stable node identifier to search for.
            api_key (str): The API key that must match the stored credential.

        Returns:
            Optional[Device]: The matching device entity, or ``None``.
        """
        try:
            model = DeviceModel.get(
                (DeviceModel.device_id == device_id) & (DeviceModel.api_key == api_key)
            )
            return DeviceRepository._to_entity(model)
        except peewee.DoesNotExist:
            return None

    @staticmethod
    def find_all() -> List[Device]:
        """Return every device currently registered at the edge."""
        return [DeviceRepository._to_entity(model) for model in DeviceModel.select()]
