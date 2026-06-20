"""Domain services for the IAM bounded context.

Domain services express business behaviour that does not fit neatly inside a
single entity.  ``DeviceService`` enforces the invariants required to provision
a valid :class:`~iam.domain.entities.Device`, while ``AuthService`` encapsulates
the device-authentication rule used to guard telemetry ingestion.
"""
import re
from datetime import datetime, timezone
from typing import Optional

from iam.domain.entities import Device

# IoT node categories registered at the edge (embedded devices).
NODE_DEVICE_TYPES = {"VITAL_SIGNS", "GPS"}

# Lifecycle states mirrored from the cloud registry.
DEVICE_STATUS_ACTIVE = "ACTIVE"
DEVICE_STATUS_REVOKED = "REVOKED"
DEVICE_STATUSES = {DEVICE_STATUS_ACTIVE, DEVICE_STATUS_REVOKED}

# Edge-server category — configured via .env, not provisioned as an IoT node.
GATEWAY_DEVICE_TYPE = "EDGE_GATEWAY"

_MAC_WITH_SEPARATORS = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


def normalize_mac_address(mac: str) -> str:
    """Normalize a MAC address to uppercase ``AA:BB:CC:DD:EE:FF`` form."""
    if not mac or not str(mac).strip():
        raise ValueError("mac_address cannot be empty")

    cleaned = str(mac).strip().upper().replace("-", ":")
    if ":" not in cleaned and len(cleaned) == 12 and re.fullmatch(r"[0-9A-F]{12}", cleaned):
        cleaned = ":".join(cleaned[i:i + 2] for i in range(0, 12, 2))

    if not _MAC_WITH_SEPARATORS.fullmatch(cleaned):
        raise ValueError("mac_address must be a valid MAC address")

    return cleaned


class DeviceService:
    """Domain service responsible for the creation of valid devices.

    Enforces the invariants of the IAM bounded context before a device is
    persisted in the edge registry:

    - ``device_id`` and ``mac_address`` must be non-empty.
    - ``device_type`` must be one of the supported categories.
    """

    @staticmethod
    def create_device(
            device_id: str,
            device_type: str,
            mac_address: str) -> Device:
        """Validate provisioning data and build a new :class:`Device` entity."""
        if not device_id or not str(device_id).strip():
            raise ValueError("device_id cannot be empty")

        normalized_mac = normalize_mac_address(mac_address)
        if device_type not in NODE_DEVICE_TYPES:
            raise ValueError("device_type must be one of VITAL_SIGNS, GPS")

        now = datetime.now(timezone.utc)
        return Device(
            device_id=str(device_id).strip(),
            device_type=device_type,
            mac_address=normalized_mac,
            status=DEVICE_STATUS_ACTIVE,
            cloud_updated_at=None,
            created_at=now,
            updated_at=now,
        )


class AuthService:
    """Domain service that determines whether a device is authenticated.

    The authentication rule is deliberately simple: a ``Device`` retrieved from
    the repository by matching its ``device_id`` and ``mac_address`` is, by
    definition, authenticated.  Absent or unrecognised credentials yield
    ``None`` and therefore ``False``.
    """

    @staticmethod
    def authenticate(device: Optional[Device]) -> bool:
        """Return whether the device is present and allowed to sign in."""
        return device is not None and device.status == DEVICE_STATUS_ACTIVE
