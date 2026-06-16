"""Domain entities for the Monitoring bounded context.

This module defines the core aggregate of the Monitoring bounded context.
Entities carry identity and encapsulate domain state; they should only be
created or mutated through domain services that enforce business invariants.
"""
from datetime import datetime
from typing import Optional


class Measurement:
    """Aggregate root representing a single vital-signs reading.

    A ``Measurement`` captures the vital signs reported by a device at a given
    point in time.  Its value structure mirrors the backend ``Measurement``
    aggregate of the Tracking bounded context so that readings can be published
    to the cloud without translation loss.  Individual vitals are optional: a
    device reports the subset of signals its sensors provide.

    Instances are created by
    :meth:`~monitoring.domain.services.MeasurementService.create_measurement`,
    which validates the raw sensor data before constructing this entity.

    Attributes:
        device_id (str): Stable backend identifier of the originating device.
        mac_address (str): Hardware MAC address of the originating device.
        nursing_home_id (int): Owning nursing-home identifier, used to route the
            reading to the correct tenant in the cloud.
        timestamp (datetime): UTC timestamp of when the reading was taken.
        heart_rate (int | None): Heart rate in beats per minute.
        systolic (int | None): Systolic blood pressure in mmHg.
        diastolic (int | None): Diastolic blood pressure in mmHg.
        temperature (float | None): Body temperature in degrees Celsius.
        oxygen_saturation (int | None): Blood oxygen saturation as a percentage.
        respiratory_rate (int | None): Respiratory rate in breaths per minute.
        synced (bool): Whether the reading has been published to the cloud.
        id (int | None): Surrogate identity assigned by the persistence layer.
    """

    def __init__(
            self,
            device_id: str,
            mac_address: str,
            nursing_home_id: int,
            timestamp: datetime,
            heart_rate: Optional[int] = None,
            systolic: Optional[int] = None,
            diastolic: Optional[int] = None,
            temperature: Optional[float] = None,
            oxygen_saturation: Optional[int] = None,
            respiratory_rate: Optional[int] = None,
            synced: bool = False,
            id: int = None):
        """Initialise a Measurement entity.

        Args:
            device_id (str): Stable backend identifier of the device.
            mac_address (str): Hardware MAC address of the device.
            nursing_home_id (int): Owning nursing-home identifier.
            timestamp (datetime): UTC timestamp of the reading.
            heart_rate (int, optional): Heart rate in beats per minute.
            systolic (int, optional): Systolic blood pressure in mmHg.
            diastolic (int, optional): Diastolic blood pressure in mmHg.
            temperature (float, optional): Body temperature in Celsius.
            oxygen_saturation (int, optional): Oxygen saturation percentage.
            respiratory_rate (int, optional): Respiratory rate in breaths/min.
            synced (bool): Cloud synchronization flag.  Defaults to ``False``.
            id (int, optional): Persistence identity.  Defaults to ``None``.
        """
        self.id = id
        self.device_id = device_id
        self.mac_address = mac_address
        self.nursing_home_id = nursing_home_id
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.systolic = systolic
        self.diastolic = diastolic
        self.temperature = temperature
        self.oxygen_saturation = oxygen_saturation
        self.respiratory_rate = respiratory_rate
        self.synced = synced
