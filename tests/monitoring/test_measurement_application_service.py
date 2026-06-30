"""Tests for MeasurementApplicationService."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from iam.domain.entities import Device
from monitoring.application.services import MeasurementApplicationService
from monitoring.domain.entities import Measurement


def _device():
    return Device(
        device_id="band-001",
        device_type="VITAL_SIGNS",
        mac_address="AA:BB:CC:DD:EE:FF",
        created_at=datetime(2026, 6, 16, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 16, tzinfo=timezone.utc),
    )


def _measurement(**overrides):
    defaults = dict(
        id=1,
        device_id="band-001",
        device_type="VITAL_SIGNS",
        timestamp=datetime(2026, 6, 16, 23, 23, tzinfo=timezone.utc),
        heart_rate=72,
    )
    return Measurement(**{**defaults, **overrides})


def _service():
    service = MeasurementApplicationService()
    service.measurement_repository = MagicMock()
    service.device_repository = MagicMock()
    service.cloud_gateway = MagicMock()
    service.registry_sync_service = MagicMock()
    return service


def test_sync_pending_marks_measurement_as_synced_when_publish_succeeds():
    service = _service()
    measurement = _measurement()
    service.measurement_repository.find_unsynced.return_value = [measurement]
    service.measurement_repository.count_unsynced.return_value = 0
    service.device_repository.find_by_device_id.return_value = _device()
    service.cloud_gateway.publish.return_value = True

    with patch("monitoring.application.services.EdgeConfig") as cfg:
        cfg.CLOUD_SYNC_ENABLED = True
        cfg.CLOUD_SYNC_BATCH_SIZE = 20
        cfg.REGISTRY_SYNC_ENABLED = False
        synced = service.sync_pending()

    assert synced == 1
    service.cloud_gateway.publish.assert_called_once_with(measurement, "AA:BB:CC:DD:EE:FF")
    service.measurement_repository.mark_as_synced.assert_called_once_with(1)
    assert measurement.synced is True


def test_sync_pending_leaves_measurement_pending_when_publish_fails():
    service = _service()
    measurement = _measurement()
    service.measurement_repository.find_unsynced.return_value = [measurement]
    service.measurement_repository.count_unsynced.return_value = 1
    service.device_repository.find_by_device_id.return_value = _device()
    service.cloud_gateway.publish.return_value = False

    with patch("monitoring.application.services.EdgeConfig") as cfg:
        cfg.CLOUD_SYNC_ENABLED = True
        cfg.CLOUD_SYNC_BATCH_SIZE = 20
        cfg.REGISTRY_SYNC_ENABLED = False
        synced = service.sync_pending()

    assert synced == 0
    service.measurement_repository.mark_as_synced.assert_not_called()
    assert measurement.synced is False
