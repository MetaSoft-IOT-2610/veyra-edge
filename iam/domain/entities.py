"""Domain entities for the IAM bounded context.

This module defines the aggregate root for the IAM bounded context.  Entities
carry identity across their lifetime and encapsulate state that is only
modified by domain services enforcing business invariants.
"""
from datetime import datetime
from typing import Optional


class Device:
    """Aggregate root representing an IoT device mirrored from the cloud registry.

    A device is identified by ``device_id`` and authenticated at sign-in through
    its paired ``mac_address``.  ``status`` and ``cloud_updated_at`` are mirrored
    from the cloud source of truth when registry sync is enabled.
    """

    def __init__(
            self,
            device_id: str,
            device_type: str,
            mac_address: str,
            created_at: datetime,
            updated_at: datetime,
            status: str = "ACTIVE",
            cloud_updated_at: Optional[datetime] = None,
            id: int = None):
        self.id = id
        self.device_id = device_id
        self.device_type = device_type
        self.mac_address = mac_address
        self.status = status
        self.cloud_updated_at = cloud_updated_at
        self.created_at = created_at
        self.updated_at = updated_at
