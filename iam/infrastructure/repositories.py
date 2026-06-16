"""Repository implementation for the IAM bounded context.

Provides the persistence adapter that maps between the
:class:`~iam.domain.entities.Device` domain entity and the
:class:`~iam.infrastructure.models.Device` Peewee ORM model.

Following the Repository pattern, callers in the application layer work only
with domain entities and remain isolated from ORM and database details.
"""
from datetime import datetime, timezone
from typing import List, Optional

import peewee

from iam.domain.entities import Device
from iam.domain.exceptions import DeviceAlreadyExistsError, DeviceNotFoundError
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
            mac_address=model.mac_address,
            nursing_home_id=model.nursing_home_id,
            device_type=model.device_type,
            api_key=model.api_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
            id=model.id,
        )

    def save(self, device: Device) -> Device:
        """Persist a new device provisioned by the backend.

        Args:
            device (Device): The transient entity to persist.

        Returns:
            Device: The persisted entity enriched with its assigned ``id``.

        Raises:
            DeviceAlreadyExistsError: If a device with the same ``device_id``
                or ``mac_address`` already exists.
        """
        try:
            model = DeviceModel.create(
                device_id=device.device_id,
                mac_address=device.mac_address,
                nursing_home_id=device.nursing_home_id,
                device_type=device.device_type,
                api_key=device.api_key,
                created_at=device.created_at,
                updated_at=device.updated_at,
            )
        except peewee.IntegrityError:
            raise DeviceAlreadyExistsError(
                f"Device already exists for device_id '{device.device_id}' "
                f"or mac_address '{device.mac_address}'"
            )
        return self._to_entity(model)

    def update_mac_address(self, device_id: str, mac_address: str) -> Device:
        """Update the MAC address of an existing device.

        Supports the backend-issued correction flow used when an operator
        mistyped the MAC address during device enrolment.

        Args:
            device_id (str): Stable backend identifier of the device to update.
            mac_address (str): The corrected hardware MAC address.

        Returns:
            Device: The updated device entity.

        Raises:
            DeviceNotFoundError: If no device matches ``device_id``.
            DeviceAlreadyExistsError: If ``mac_address`` is already used by
                another device.
        """
        try:
            model = DeviceModel.get(DeviceModel.device_id == device_id)
        except peewee.DoesNotExist:
            raise DeviceNotFoundError(f"Device not found for device_id '{device_id}'")

        model.mac_address = mac_address
        model.updated_at = datetime.now(timezone.utc)
        try:
            model.save()
        except peewee.IntegrityError:
            raise DeviceAlreadyExistsError(
                f"mac_address '{mac_address}' is already in use by another device"
            )
        return self._to_entity(model)

    def find_by_device_id(self, device_id: str) -> Optional[Device]:
        """Look up a device by its stable backend identifier."""
        try:
            model = DeviceModel.get(DeviceModel.device_id == device_id)
            return self._to_entity(model)
        except peewee.DoesNotExist:
            return None

    def find_by_mac_and_api_key(self, mac_address: str, api_key: str) -> Optional[Device]:
        """Look up a device by its MAC address and API key.

        Used to authenticate inbound telemetry.  Returns ``None`` (rather than
        raising) when no match is found, letting the domain service apply the
        authentication rule without catching infrastructure exceptions.

        Args:
            mac_address (str): The hardware MAC address to search for.
            api_key (str): The API key that must match the stored credential.

        Returns:
            Optional[Device]: The matching device entity, or ``None``.
        """
        try:
            model = DeviceModel.get(
                (DeviceModel.mac_address == mac_address) & (DeviceModel.api_key == api_key)
            )
            return self._to_entity(model)
        except peewee.DoesNotExist:
            return None

    def find_all(self) -> List[Device]:
        """Return every device currently registered at the edge."""
        return [self._to_entity(model) for model in DeviceModel.select()]
