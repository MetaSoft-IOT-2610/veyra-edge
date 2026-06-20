"""Repository implementation for the IAM bounded context."""
from datetime import datetime, timezone
from typing import Any, List, Optional

import peewee

from iam.domain.entities import Device
from iam.domain.exceptions import DeviceAlreadyExistsError
from iam.domain.services import (
    DEVICE_STATUSES,
    DEVICE_STATUS_ACTIVE,
    normalize_mac_address,
)
from iam.infrastructure.models import Device as DeviceModel
from iam.infrastructure.registry_sync import CloudRegistryGateway


class DeviceRepository:
    """Repository that persists and reconstructs :class:`~iam.domain.entities.Device` entities."""

    @staticmethod
    def _to_entity(model: DeviceModel) -> Device:
        return Device(
            device_id=model.device_id,
            device_type=model.device_type,
            mac_address=model.mac_address,
            status=model.status,
            cloud_updated_at=model.cloud_updated_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            id=model.id,
        )

    @staticmethod
    def save(device: Device) -> Device:
        try:
            model = DeviceModel.create(
                device_id=device.device_id,
                device_type=device.device_type,
                mac_address=device.mac_address,
                status=device.status,
                cloud_updated_at=device.cloud_updated_at,
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
        try:
            model = DeviceModel.get(
                (DeviceModel.device_id == device_id) & (DeviceModel.status == DEVICE_STATUS_ACTIVE)
            )
            return DeviceRepository._to_entity(model)
        except peewee.DoesNotExist:
            return None

    @staticmethod
    def find_by_id_and_mac_address(device_id: str, mac_address: str) -> Optional[Device]:
        try:
            normalized_mac = normalize_mac_address(mac_address)
            model = DeviceModel.get(
                (DeviceModel.device_id == device_id)
                & (DeviceModel.mac_address == normalized_mac)
                & (DeviceModel.status == DEVICE_STATUS_ACTIVE)
            )
            return DeviceRepository._to_entity(model)
        except (peewee.DoesNotExist, ValueError):
            return None

    @staticmethod
    def find_all() -> List[Device]:
        return [DeviceRepository._to_entity(model) for model in DeviceModel.select()]

    @staticmethod
    def get_max_cloud_updated_at() -> Optional[datetime]:
        query = DeviceModel.select(peewee.fn.MAX(DeviceModel.cloud_updated_at))
        value = query.scalar()
        return value

    @staticmethod
    def upsert_from_cloud(entry: dict[str, Any]) -> bool:
        """Create or update a device row from a cloud registry entry."""
        device_id = str(entry["device_id"]).strip()
        device_type = str(entry["device_type"]).strip()
        mac_address = normalize_mac_address(str(entry["mac_address"]))
        status = str(entry.get("status", DEVICE_STATUS_ACTIVE)).strip().upper()
        if status not in DEVICE_STATUSES:
            raise ValueError(f"Unsupported device status '{status}'")

        cloud_updated_at = CloudRegistryGateway.parse_cloud_updated_at(
            entry.get("updated_at") or entry.get("cloud_updated_at")
        )
        now = datetime.now(timezone.utc)

        try:
            model = DeviceModel.get(DeviceModel.device_id == device_id)
        except peewee.DoesNotExist:
            DeviceModel.create(
                device_id=device_id,
                device_type=device_type,
                mac_address=mac_address,
                status=status,
                cloud_updated_at=cloud_updated_at,
                created_at=now,
                updated_at=now,
            )
            return True

        changed = (
            model.device_type != device_type
            or model.mac_address != mac_address
            or model.status != status
            or model.cloud_updated_at != cloud_updated_at
        )
        if not changed:
            return False

        model.device_type = device_type
        model.mac_address = mac_address
        model.status = status
        model.cloud_updated_at = cloud_updated_at
        model.updated_at = now
        model.save()
        return True
