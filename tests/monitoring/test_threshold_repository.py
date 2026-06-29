"""Tests for ThresholdRepository (uses in-memory SQLite via the db fixture)."""
from datetime import datetime, timezone

import pytest

from monitoring.infrastructure.threshold_repository import ThresholdRepository

NOW = datetime(2026, 6, 29, 10, 0, 0, tzinfo=timezone.utc)

_ENTRY = {
    "device_id": "band-001",
    "heart_rate_min": 50,
    "heart_rate_max": 120,
    "systolic_min": 90,
    "systolic_max": 140,
    "diastolic_min": 60,
    "diastolic_max": 90,
    "temperature_min": 35.0,
    "temperature_max": 38.5,
    "oxygen_saturation_min": 90,
    "oxygen_saturation_max": 100,
    "respiratory_rate_min": 12,
    "respiratory_rate_max": 20,
    "updated_at": "2026-06-29T10:00:00Z",
}


# --- upsert_from_cloud ---

def test_upsert_creates_new_record(db):
    result = ThresholdRepository.upsert_from_cloud(_ENTRY)
    assert result is True


def test_upsert_persists_all_fields(db):
    ThresholdRepository.upsert_from_cloud(_ENTRY)
    t = ThresholdRepository.find_by_device_id("band-001")
    assert t.device_id == "band-001"
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
    assert t.cloud_updated_at is not None


def test_upsert_stores_partial_fields(db):
    ThresholdRepository.upsert_from_cloud({"device_id": "band-002", "heart_rate_max": 110})
    t = ThresholdRepository.find_by_device_id("band-002")
    assert t.heart_rate_max == 110
    assert t.heart_rate_min is None
    assert t.temperature_min is None


def test_upsert_returns_false_when_record_unchanged(db):
    ThresholdRepository.upsert_from_cloud(_ENTRY)
    result = ThresholdRepository.upsert_from_cloud(_ENTRY)
    assert result is False


def test_upsert_returns_true_and_updates_when_field_changed(db):
    ThresholdRepository.upsert_from_cloud(_ENTRY)
    updated = {**_ENTRY, "heart_rate_max": 130, "updated_at": "2026-06-30T00:00:00Z"}
    result = ThresholdRepository.upsert_from_cloud(updated)
    assert result is True
    t = ThresholdRepository.find_by_device_id("band-001")
    assert t.heart_rate_max == 130


def test_upsert_raises_on_missing_device_id(db):
    with pytest.raises((KeyError, Exception)):
        ThresholdRepository.upsert_from_cloud({"heart_rate_min": 50})


# --- find_by_device_id ---

def test_find_by_device_id_returns_entity(db):
    ThresholdRepository.upsert_from_cloud(_ENTRY)
    t = ThresholdRepository.find_by_device_id("band-001")
    assert t is not None
    assert t.device_id == "band-001"


def test_find_by_device_id_returns_none_when_missing(db):
    assert ThresholdRepository.find_by_device_id("nonexistent") is None


# --- find_all ---

def test_find_all_returns_empty_list_when_no_records(db):
    assert ThresholdRepository.find_all() == []


def test_find_all_returns_all_records(db):
    ThresholdRepository.upsert_from_cloud(_ENTRY)
    ThresholdRepository.upsert_from_cloud({**_ENTRY, "device_id": "band-002"})
    all_t = ThresholdRepository.find_all()
    assert len(all_t) == 2
    device_ids = {t.device_id for t in all_t}
    assert device_ids == {"band-001", "band-002"}


# --- get_max_cloud_updated_at ---

def test_get_max_cloud_updated_at_returns_none_when_empty(db):
    assert ThresholdRepository.get_max_cloud_updated_at() is None


def test_get_max_cloud_updated_at_returns_latest(db):
    ThresholdRepository.upsert_from_cloud({**_ENTRY, "updated_at": "2026-06-01T00:00:00Z"})
    ThresholdRepository.upsert_from_cloud({**_ENTRY, "device_id": "band-002", "updated_at": "2026-06-29T10:00:00Z"})
    max_ts = ThresholdRepository.get_max_cloud_updated_at()
    assert max_ts is not None
    assert "2026-06-29" in str(max_ts)
