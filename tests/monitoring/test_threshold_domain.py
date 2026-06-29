"""Tests for the Threshold domain entity."""
from datetime import datetime, timezone

from monitoring.domain.entities import Threshold


def test_threshold_defaults_all_bounds_to_none():
    t = Threshold(device_id="band-001")
    assert t.device_id == "band-001"
    assert t.id is None
    assert t.heart_rate_min is None
    assert t.heart_rate_max is None
    assert t.systolic_min is None
    assert t.systolic_max is None
    assert t.diastolic_min is None
    assert t.diastolic_max is None
    assert t.temperature_min is None
    assert t.temperature_max is None
    assert t.oxygen_saturation_min is None
    assert t.oxygen_saturation_max is None
    assert t.respiratory_rate_min is None
    assert t.respiratory_rate_max is None
    assert t.cloud_updated_at is None


def test_threshold_stores_all_fields():
    ts = datetime(2026, 6, 29, 10, 0, 0, tzinfo=timezone.utc)
    t = Threshold(
        device_id="band-002",
        heart_rate_min=50,
        heart_rate_max=120,
        systolic_min=90,
        systolic_max=140,
        diastolic_min=60,
        diastolic_max=90,
        temperature_min=35.0,
        temperature_max=38.5,
        oxygen_saturation_min=90,
        oxygen_saturation_max=100,
        respiratory_rate_min=12,
        respiratory_rate_max=20,
        cloud_updated_at=ts,
        id=7,
    )
    assert t.id == 7
    assert t.device_id == "band-002"
    assert t.heart_rate_min == 50
    assert t.heart_rate_max == 120
    assert t.systolic_min == 90
    assert t.systolic_max == 140
    assert t.diastolic_min == 60
    assert t.diastolic_max == 90
    assert t.temperature_min == 35.0
    assert t.temperature_max == 38.5
    assert t.oxygen_saturation_min == 90
    assert t.oxygen_saturation_max == 100
    assert t.respiratory_rate_min == 12
    assert t.respiratory_rate_max == 20
    assert t.cloud_updated_at == ts
