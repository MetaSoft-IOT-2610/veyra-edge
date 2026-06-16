"""Domain entities for the IAM bounded context.

This module defines the aggregate root for the IAM bounded context.  Entities
carry identity across their lifetime and encapsulate state that is only
modified by domain services enforcing business invariants.
"""
from datetime import datetime


class Device:
    """Aggregate root representing an IoT device provisioned at the edge.

    Unlike a purely local edge service, Veyra devices are provisioned from the
    cloud backend: the backend pushes the device registry to the edge so the
    edge can authenticate telemetry and tag it with the owning nursing home.

    A ``Device`` is identified internally by ``device_id`` (the stable
    identifier assigned by the backend) and authenticates telemetry through its
    ``mac_address`` paired with its ``api_key``.  The ``mac_address`` is mutable
    because an operator may have mistyped it during enrolment; it is corrected
    via a backend-issued update.

    Attributes:
        device_id (str): Stable identifier assigned by the cloud backend.
        mac_address (str): Hardware MAC address used by the physical device to
            identify itself when sending telemetry.  Mutable.
        nursing_home_id (int): Identifier of the nursing home the device
            belongs to, used to route telemetry to the correct tenant.
        device_type (str): Device category (``'VITAL_SIGNS'`` or ``'GPS'``).
        api_key (str): Secret key used to authenticate telemetry requests,
            transmitted via the ``X-API-Key`` header.
        created_at (datetime): UTC timestamp of when the device was registered
            at the edge.
        updated_at (datetime): UTC timestamp of the last update applied to the
            device (e.g. a MAC-address correction).
        id (int | None): Surrogate identity assigned by the persistence layer.
            ``None`` for transient (unsaved) instances.
    """

    def __init__(
            self,
            device_id: str,
            mac_address: str,
            nursing_home_id: int,
            device_type: str,
            api_key: str,
            created_at: datetime,
            updated_at: datetime,
            id: int = None):
        """Initialise a Device aggregate root.

        Args:
            device_id (str): Stable identifier assigned by the backend.
            mac_address (str): Hardware MAC address of the device.
            nursing_home_id (int): Owning nursing-home identifier.
            device_type (str): Device category (``'VITAL_SIGNS'`` or ``'GPS'``).
            api_key (str): Secret API key used for telemetry authentication.
            created_at (datetime): UTC timestamp of device registration.
            updated_at (datetime): UTC timestamp of the last update.
            id (int, optional): Persistence identity.  Defaults to ``None``.
        """
        self.id = id
        self.device_id = device_id
        self.mac_address = mac_address
        self.nursing_home_id = nursing_home_id
        self.device_type = device_type
        self.api_key = api_key
        self.created_at = created_at
        self.updated_at = updated_at
