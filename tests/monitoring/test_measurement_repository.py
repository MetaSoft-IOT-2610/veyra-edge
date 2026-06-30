"""Tests for MeasurementRepository."""
from datetime import datetime, timezone

import peewee
import pytest

from monitoring.domain.entities import Measurement
from monitoring.infrastructure.models import Measurement as MeasurementModel
from monitoring.infrastructure.repositories import MeasurementRepository

TEST_DB = peewee.SqliteDatabase(":memory:")


@pytest.fixture
def db():
    with TEST_DB.bind_ctx([MeasurementModel]):
        TEST_DB.connect()
        TEST_DB.create_tables([MeasurementModel])
        yield TEST_DB
        TEST_DB.drop_tables([MeasurementModel])
        TEST_DB.close()


def _measurement(**overrides):
    defaults = dict(
        device_id="band-001",
        device_type="VITAL_SIGNS",
        timestamp=datetime(2026, 6, 16, 23, 23, tzinfo=timezone.utc),
        heart_rate=72,
    )
    return Measurement(**{**defaults, **overrides})


def test_save_persists_measurement_with_diagnostics(db):
    saved = MeasurementRepository.save(
        _measurement(diagnostics={"max30102_status": "ok"}, latitude=-12.0, longitude=-77.0)
    )

    assert saved.id is not None
    assert saved.diagnostics == {"max30102_status": "ok"}
    assert saved.latitude == -12.0
    assert saved.longitude == -77.0
    assert saved.synced is False


def test_find_unsynced_returns_oldest_pending_measurements_first(db):
    first = MeasurementRepository.save(_measurement(heart_rate=70))
    second = MeasurementRepository.save(_measurement(heart_rate=71))
    synced = MeasurementRepository.save(_measurement(heart_rate=72))
    MeasurementRepository.mark_as_synced(synced.id)

    pending = MeasurementRepository.find_unsynced()

    assert [m.id for m in pending] == [first.id, second.id]


def test_find_unsynced_applies_limit(db):
    MeasurementRepository.save(_measurement(heart_rate=70))
    MeasurementRepository.save(_measurement(heart_rate=71))

    pending = MeasurementRepository.find_unsynced(limit=1)

    assert len(pending) == 1


def test_mark_as_synced_removes_measurement_from_pending_count(db):
    saved = MeasurementRepository.save(_measurement())

    assert MeasurementRepository.count_unsynced() == 1

    MeasurementRepository.mark_as_synced(saved.id)

    assert MeasurementRepository.count_unsynced() == 0
