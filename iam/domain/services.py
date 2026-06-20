"""Domain services for the IAM bounded context.

Domain services express business behaviour that does not fit neatly inside a
single entity.  ``DeviceService`` enforces the invariants required to provision
a valid :class:`~iam.domain.entities.Device`, while ``AuthService`` encapsulates
the device-authentication rule used to guard telemetry ingestion.
"""
from datetime import datetime, timezone
from typing import Optional

from iam.domain.entities import Device

# IoT node categories registered at the edge (embedded devices).
NODE_DEVICE_TYPES = {"VITAL_SIGNS", "GPS"}

# Edge-server category — configured via .env, not provisioned as an IoT node.
GATEWAY_DEVICE_TYPE = "EDGE_GATEWAY"


class DeviceService:
    """Domain service responsible for the creation of valid devices.

    Enforces the invariants of the IAM bounded context before a device is
    persisted in the edge registry:

    - ``device_id`` and ``api_key`` must be non-empty.
    - ``device_type`` must be one of the supported categories.
    """

    @staticmethod
    def create_device(
            device_id: str,
            device_type: str,
            api_key: str) -> Device:
        """Validate provisioning data and build a new :class:`Device` entity.

        Args:
            device_id (str): Stable node identifier assigned by the backend.
            device_type (str): Node category (``'VITAL_SIGNS'`` or ``'GPS'``).
            api_key (str): Secret API key used for telemetry authentication.

        Returns:
            Device: A new, unsaved :class:`~iam.domain.entities.Device` entity
            with ``created_at`` / ``updated_at`` set to the current UTC time.

        Raises:
            ValueError: If any required field is missing or invalid.
        """
        if not device_id or not str(device_id).strip():
            raise ValueError("device_id cannot be empty")
        if not api_key or not str(api_key).strip():
            raise ValueError("api_key cannot be empty")
        if device_type not in NODE_DEVICE_TYPES:
            raise ValueError("device_type must be one of VITAL_SIGNS, GPS")

        now = datetime.now(timezone.utc)
        return Device(
            device_id=str(device_id).strip(),
            device_type=device_type,
            api_key=str(api_key).strip(),
            created_at=now,
            updated_at=now,
        )


class AuthService:
    """Domain service that determines whether a device is authenticated.

    The authentication rule is deliberately simple: a ``Device`` retrieved from
    the repository by matching its ``device_id`` and ``api_key`` is, by
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
