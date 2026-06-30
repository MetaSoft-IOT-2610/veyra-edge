"""Tests for measurement domain validation."""
import pytest

from monitoring.domain.services import MeasurementService


def _create_measurement(**overrides):
    defaults = dict(
        device_id="band-001",
        device_type="VITAL_SIGNS",
        heart_rate=None,
        systolic=None,
        diastolic=None,
        temperature=None,
        oxygen_saturation=None,
        respiratory_rate=None,
        ambient_temperature=None,
        latitude=None,
        longitude=None,
        satellite_count=None,
        satellites_in_view=None,
        timestamp="2026-06-16T18:23:00-05:00",
        diagnostics=None,
    )
    return MeasurementService.create_measurement(**{**defaults, **overrides})


def test_create_measurement_rejects_empty_payload():
    with pytest.raises(ValueError, match="At least one vital sign or GPS location"):
        _create_measurement()


def test_create_measurement_requires_vital_sign_for_vital_signs_device():
    with pytest.raises(ValueError, match="At least one vital sign or GPS location"):
        _create_measurement(latitude=-12.0464, longitude=-77.0428, diagnostics={"gps_status": "fix_ok"})


def test_create_measurement_accepts_heart_rate_as_publishable_vital():
    measurement = _create_measurement(heart_rate=72)

    assert measurement.heart_rate == 72


def test_create_measurement_accepts_blood_pressure_as_publishable_vital():
    measurement = _create_measurement(systolic=120, diastolic=80)

    assert measurement.systolic == 120
    assert measurement.diastolic == 80


def test_create_measurement_accepts_respiratory_rate_as_publishable_vital():
    measurement = _create_measurement(respiratory_rate=18)

    assert measurement.respiratory_rate == 18


def test_create_measurement_accepts_location_for_gps_device():
    measurement = _create_measurement(
        device_type="GPS",
        latitude=-12.0464,
        longitude=-77.0428,
        diagnostics={"gps_status": "fix_ok"},
    )

    assert measurement.device_type == "GPS"
    assert measurement.latitude == -12.0464
    assert measurement.longitude == -77.0428
