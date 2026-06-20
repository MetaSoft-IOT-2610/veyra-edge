"""Domain entities for the IAM bounded context.

This module defines the aggregate root for the IAM bounded context.  Entities
carry identity across their lifetime and encapsulate state that is only
modified by domain services enforcing business invariants.
"""
from datetime import datetime


class Device:
    """Aggregate root representing an IoT device provisioned at the edge.

    A device is identified by ``device_id`` (stable node identifier) and
    authenticated on telemetry requests through its paired ``api_key``.

    Attributes:
        device_id (str): Stable node identifier assigned by the backend.
        device_type (str): Device category (``'VITAL_SIGNS'`` or ``'GPS'``).
        api_key (str): Secret key used to authenticate telemetry requests,
            transmitted via the ``X-API-Key`` header.
        created_at (datetime): UTC timestamp of when the device was registered
            at the edge.
        updated_at (datetime): UTC timestamp of the last update applied to the
            device.
        id (int | None): Surrogate identity assigned by the persistence layer.
            ``None`` for transient (unsaved) instances.
    """

    def __init__(
            self,
            device_id: str,
            device_type: str,
            api_key: str,
            created_at: datetime,
            updated_at: datetime,
            id: int = None):
        """Initialise a Device aggregate root.

        Args:
            device_id (str): Stable node identifier assigned by the backend.
            device_type (str): Device category (``'VITAL_SIGNS'`` or ``'GPS'``).
            api_key (str): Secret API key used for telemetry authentication.
            created_at (datetime): UTC timestamp of device registration.
            updated_at (datetime): UTC timestamp of the last update.
            id (int, optional): Persistence identity.  Defaults to ``None``.
        """
        self.id = id
        self.device_id = device_id
        self.device_type = device_type
        self.api_key = api_key
        self.created_at = created_at
        self.updated_at = updated_at
