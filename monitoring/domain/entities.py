"""Domain entities for the Monitoring bounded context.

This module defines the core aggregate of the Monitoring bounded context.
Entities carry identity and encapsulate domain state; they should only be
created or mutated through domain services that enforce business invariants.
"""
from datetime import datetime
from typing import Any, Optional


class Threshold:
    """Vital-sign alert bounds mirrored from the cloud for a single device.

    Each instance represents the set of min/max bounds the cloud has configured
    for a given ``device_id``.  All bounds are optional: the cloud may only
    define thresholds for a subset of vitals.

    Attributes:
        device_id (str): Stable node identifier this threshold record belongs to.
        heart_rate_min (int | None): Lower alert bound for heart rate (bpm).
        heart_rate_max (int | None): Upper alert bound for heart rate (bpm).
        systolic_min (int | None): Lower alert bound for systolic pressure (mmHg).
        systolic_max (int | None): Upper alert bound for systolic pressure (mmHg).
        diastolic_min (int | None): Lower alert bound for diastolic pressure (mmHg).
        diastolic_max (int | None): Upper alert bound for diastolic pressure (mmHg).
        temperature_min (float | None): Lower alert bound for temperature (°C).
        temperature_max (float | None): Upper alert bound for temperature (°C).
        oxygen_saturation_min (int | None): Lower alert bound for SpO₂ (%).
        oxygen_saturation_max (int | None): Upper alert bound for SpO₂ (%).
        respiratory_rate_min (int | None): Lower alert bound for resp. rate (breaths/min).
        respiratory_rate_max (int | None): Upper alert bound for resp. rate (breaths/min).
        cloud_updated_at (datetime | None): UTC timestamp of the last cloud update.
        id (int | None): Surrogate identity assigned by the persistence layer.
    """

    def __init__(
            self,
            device_id: str,
            heart_rate_min: Optional[int] = None,
            heart_rate_max: Optional[int] = None,
            systolic_min: Optional[int] = None,
            systolic_max: Optional[int] = None,
            diastolic_min: Optional[int] = None,
            diastolic_max: Optional[int] = None,
            temperature_min: Optional[float] = None,
            temperature_max: Optional[float] = None,
            oxygen_saturation_min: Optional[int] = None,
            oxygen_saturation_max: Optional[int] = None,
            respiratory_rate_min: Optional[int] = None,
            respiratory_rate_max: Optional[int] = None,
            cloud_updated_at: Optional[datetime] = None,
            id: int = None):
        self.id = id
        self.device_id = device_id
        self.heart_rate_min = heart_rate_min
        self.heart_rate_max = heart_rate_max
        self.systolic_min = systolic_min
        self.systolic_max = systolic_max
        self.diastolic_min = diastolic_min
        self.diastolic_max = diastolic_max
        self.temperature_min = temperature_min
        self.temperature_max = temperature_max
        self.oxygen_saturation_min = oxygen_saturation_min
        self.oxygen_saturation_max = oxygen_saturation_max
        self.respiratory_rate_min = respiratory_rate_min
        self.respiratory_rate_max = respiratory_rate_max
        self.cloud_updated_at = cloud_updated_at

    def is_violated_by(self, measurement: "Measurement") -> bool:
        """Check if any vital sign in the measurement violates these thresholds."""
        if measurement.heart_rate is not None:
            if self.heart_rate_min is not None and measurement.heart_rate < self.heart_rate_min:
                return True
            if self.heart_rate_max is not None and measurement.heart_rate > self.heart_rate_max:
                return True

        if measurement.systolic is not None:
            if self.systolic_min is not None and measurement.systolic < self.systolic_min:
                return True
            if self.systolic_max is not None and measurement.systolic > self.systolic_max:
                return True

        if measurement.diastolic is not None:
            if self.diastolic_min is not None and measurement.diastolic < self.diastolic_min:
                return True
            if self.diastolic_max is not None and measurement.diastolic > self.diastolic_max:
                return True

        if measurement.temperature is not None:
            if self.temperature_min is not None and measurement.temperature < self.temperature_min:
                return True
            if self.temperature_max is not None and measurement.temperature > self.temperature_max:
                return True

        if measurement.oxygen_saturation is not None:
            if self.oxygen_saturation_min is not None and measurement.oxygen_saturation < self.oxygen_saturation_min:
                return True
            if self.oxygen_saturation_max is not None and measurement.oxygen_saturation > self.oxygen_saturation_max:
                return True

        if measurement.respiratory_rate is not None:
            if self.respiratory_rate_min is not None and measurement.respiratory_rate < self.respiratory_rate_min:
                return True
            if self.respiratory_rate_max is not None and measurement.respiratory_rate > self.respiratory_rate_max:
                return True

        return False



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
