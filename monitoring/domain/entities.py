"""Domain entities for the Monitoring bounded context.

This module defines the core aggregate of the Monitoring bounded context.
Entities carry identity and encapsulate domain state; they should only be
created or mutated through domain services that enforce business invariants.
"""
from datetime import datetime
from typing import Any, Optional


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
        device_id (str): Stable node identifier of the originating device.
        device_type (str): Device category from gateway registry (``VITAL_SIGNS`` / ``GPS``).
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
            device_type: str,
            timestamp: datetime,
            heart_rate: Optional[int] = None,
            systolic: Optional[int] = None,
            diastolic: Optional[int] = None,
            temperature: Optional[float] = None,
            oxygen_saturation: Optional[int] = None,
            respiratory_rate: Optional[int] = None,
            ambient_temperature: Optional[float] = None,
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
            satellite_count: Optional[int] = None,
            satellites_in_view: Optional[int] = None,
            diagnostics: Optional[dict[str, Any]] = None,
            synced: bool = False,
            id: int = None):
        """Initialise a Measurement entity.

        Args:
            device_id (str): Stable node identifier of the device.
            device_type (str): Device category assigned at the gateway.
            timestamp (datetime): UTC timestamp of the reading.
            heart_rate (int, optional): Heart rate in beats per minute.
            systolic (int, optional): Systolic blood pressure in mmHg.
            diastolic (int, optional): Diastolic blood pressure in mmHg.
            temperature (float, optional): Body temperature in Celsius.
            oxygen_saturation (int, optional): Oxygen saturation percentage.
            respiratory_rate (int, optional): Respiratory rate in breaths/min.
            ambient_temperature (float, optional): Ambient temperature in Celsius.
            latitude (float, optional): GPS latitude in decimal degrees.
            longitude (float, optional): GPS longitude in decimal degrees.
            satellite_count (int, optional): Satellites used for fix.
            satellites_in_view (int, optional): Satellites in view.
            diagnostics (dict, optional): Per-sensor health snapshot from the node.
            synced (bool): Cloud synchronization flag.  Defaults to ``False``.
            id (int, optional): Persistence identity.  Defaults to ``None``.
        """
        self.id = id
        self.device_id = device_id
        self.device_type = device_type
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.systolic = systolic
        self.diastolic = diastolic
        self.temperature = temperature
        self.oxygen_saturation = oxygen_saturation
        self.respiratory_rate = respiratory_rate
        self.ambient_temperature = ambient_temperature
        self.latitude = latitude
        self.longitude = longitude
        self.satellite_count = satellite_count
        self.satellites_in_view = satellites_in_view
        self.diagnostics = diagnostics
        self.synced = synced
