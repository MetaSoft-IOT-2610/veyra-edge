"""Domain services for the Monitoring bounded context.

``MeasurementService`` validates raw vital-signs sensor input and constructs a
well-formed :class:`~monitoring.domain.entities.Measurement` aggregate.  The
validation ranges intentionally match the value-object invariants of the
backend Tracking bounded context (``HeartRate``, ``BloodPressure``,
``Temperature``, ``OxygenSaturation``, ``RespiratoryRate``) so that any reading
accepted at the edge is also accepted by the cloud.
"""
from datetime import datetime, timezone
from typing import Optional

from dateutil.parser import parse

from iam.domain.entities import Device
from monitoring.domain.entities import Measurement


class MeasurementService:
    """Domain service responsible for the creation of valid measurements.

    Enforces the vital-signs invariants of the Monitoring bounded context.
    Every vital is optional, but any value that is provided must fall within
    its physiologically plausible range, and blood pressure must be reported as
    a consistent systolic/diastolic pair.
    """

    @staticmethod
    def create_measurement(
            device: Device,
            heart_rate: Optional[int],
            systolic: Optional[int],
            diastolic: Optional[int],
            temperature: Optional[float],
            oxygen_saturation: Optional[int],
            respiratory_rate: Optional[int],
            timestamp: Optional[str]) -> Measurement:
        """Validate raw sensor data and create a :class:`Measurement` entity.

        Args:
            device (Device): The authenticated device that produced the reading;
                supplies ``device_id``, ``mac_address`` and ``nursing_home_id``.
            heart_rate (int | None): Heart rate in beats per minute [0, 300].
            systolic (int | None): Systolic blood pressure in mmHg [0, 300].
            diastolic (int | None): Diastolic blood pressure in mmHg [0, 200].
            temperature (float | None): Temperature in Celsius [30.0, 45.0].
            oxygen_saturation (int | None): Oxygen saturation percentage [0, 100].
            respiratory_rate (int | None): Respiratory rate in breaths/min [0, 60].
            timestamp (str | None): ISO 8601 timestamp of the reading; defaults
                to the current UTC time when omitted.

        Returns:
            Measurement: A new, unsaved measurement with a UTC-normalized
            ``timestamp``.

        Raises:
            ValueError: If any provided value is out of range, the
                systolic/diastolic pair is inconsistent, or the timestamp is
                malformed.
        """
        parsed_timestamp = MeasurementService._parse_timestamp(timestamp)

        heart_rate = MeasurementService._validate_int(
            heart_rate, "heart_rate", 0, 300)
        temperature = MeasurementService._validate_float(
            temperature, "temperature", 30.0, 45.0)
        oxygen_saturation = MeasurementService._validate_int(
            oxygen_saturation, "oxygen_saturation", 0, 100)
        respiratory_rate = MeasurementService._validate_int(
            respiratory_rate, "respiratory_rate", 0, 60)
        systolic, diastolic = MeasurementService._validate_blood_pressure(systolic, diastolic)

        return Measurement(
            device_id=device.device_id,
            mac_address=device.mac_address,
            nursing_home_id=device.nursing_home_id,
            timestamp=parsed_timestamp,
            heart_rate=heart_rate,
            systolic=systolic,
            diastolic=diastolic,
            temperature=temperature,
            oxygen_saturation=oxygen_saturation,
            respiratory_rate=respiratory_rate,
        )

    @staticmethod
    def _parse_timestamp(timestamp: Optional[str]) -> datetime:
        """Parse an ISO 8601 timestamp to UTC, defaulting to the current time."""
        if not timestamp:
            return datetime.now(timezone.utc)
        try:
            return parse(timestamp).astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            raise ValueError("Invalid timestamp format")

    @staticmethod
    def _validate_int(value, name: str, minimum: int, maximum: int) -> Optional[int]:
        """Validate an optional integer vital against an inclusive range."""
        if value is None:
            return None
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{name} must be an integer")
        if not (minimum <= value <= maximum):
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return value

    @staticmethod
    def _validate_float(value, name: str, minimum: float, maximum: float) -> Optional[float]:
        """Validate an optional float vital against an inclusive range."""
        if value is None:
            return None
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"{name} must be a number")
        if not (minimum <= value <= maximum):
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return value

    @staticmethod
    def _validate_blood_pressure(systolic, diastolic):
        """Validate the systolic/diastolic pair as a consistent unit.

        Both readings must be supplied together, each within range, with
        systolic strictly greater than diastolic — mirroring the backend
        ``BloodPressure`` value object.
        """
        if systolic is None and diastolic is None:
            return None, None
        if systolic is None or diastolic is None:
            raise ValueError("systolic and diastolic must be provided together")
        systolic = MeasurementService._validate_int(systolic, "systolic", 0, 300)
        diastolic = MeasurementService._validate_int(diastolic, "diastolic", 0, 200)
        if systolic <= diastolic:
            raise ValueError("systolic must be greater than diastolic")
        return systolic, diastolic
