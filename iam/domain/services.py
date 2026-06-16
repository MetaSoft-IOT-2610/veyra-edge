"""Domain services for the IAM bounded context.

Domain services express business behaviour that does not fit neatly inside a
single entity.  ``DeviceService`` enforces the invariants required to provision
a valid :class:`~iam.domain.entities.Device`, while ``AuthService`` encapsulates
the device-authentication rule used to guard telemetry ingestion.
"""
from datetime import datetime, timezone
from typing import Optional

from iam.domain.entities import Device

# Device categories accepted by the edge, aligned with the backend
# ``DeviceType`` enumeration of the Tracking bounded context.
VALID_DEVICE_TYPES = {"VITAL_SIGNS", "GPS"}


class DeviceService:
    """Domain service responsible for the creation of valid devices.

    Enforces the invariants of the IAM bounded context before a device is
    persisted in the edge registry:

    - ``device_id``, ``mac_address`` and ``api_key`` must be non-empty.
    - ``nursing_home_id`` must be a valid integer identifier.
    - ``device_type`` must be one of the supported categories.
    """

    @staticmethod
    def create_device(
            device_id: str,
            mac_address: str,
            nursing_home_id: int,
            device_type: str,
            api_key: str) -> Device:
        """Validate provisioning data and build a new :class:`Device` entity.

        Args:
            device_id (str): Stable identifier assigned by the backend.
            mac_address (str): Hardware MAC address of the device.
            nursing_home_id (int): Owning nursing-home identifier.
            device_type (str): Device category (``'VITAL_SIGNS'`` or ``'GPS'``).
            api_key (str): Secret API key used for telemetry authentication.

        Returns:
            Device: A new, unsaved :class:`~iam.domain.entities.Device` entity
            with ``created_at`` / ``updated_at`` set to the current UTC time.

        Raises:
            ValueError: If any required field is missing or invalid.
        """
        if not device_id or not str(device_id).strip():
            raise ValueError("device_id cannot be empty")
        if not mac_address or not str(mac_address).strip():
            raise ValueError("mac_address cannot be empty")
        if not api_key or not str(api_key).strip():
            raise ValueError("api_key cannot be empty")
        if device_type not in VALID_DEVICE_TYPES:
            raise ValueError("device_type must be one of VITAL_SIGNS, GPS")
        try:
            nursing_home_id = int(nursing_home_id)
        except (TypeError, ValueError):
            raise ValueError("nursing_home_id must be an integer")

        now = datetime.now(timezone.utc)
        return Device(
            device_id=str(device_id).strip(),
            mac_address=str(mac_address).strip(),
            nursing_home_id=nursing_home_id,
            device_type=device_type,
            api_key=str(api_key).strip(),
            created_at=now,
            updated_at=now,
        )


class AuthService:
    """Domain service that determines whether a device is authenticated.

    The authentication rule is deliberately simple: a ``Device`` retrieved from
    the repository by matching its ``mac_address`` and ``api_key`` is, by
    definition, authenticated.  Absent or unrecognised credentials yield
    ``None`` and therefore ``False``.
    """

    @staticmethod
    def authenticate(device: Optional[Device]) -> bool:
        """Return whether the given device look-up constitutes a valid identity.

        Args:
            device (Optional[Device]): The device returned by the repository,
                or ``None`` when no matching device was found.

        Returns:
            bool: ``True`` if ``device`` is not ``None``; ``False`` otherwise.
        """
        return device is not None
