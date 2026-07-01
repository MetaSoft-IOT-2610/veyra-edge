"""Tests for MeasurementApplicationService."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from iam.domain.entities import Device
from monitoring.application.services import MeasurementApplicationService
from monitoring.domain.entities import Measurement, Threshold


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
    service.threshold_sync_service = MagicMock()
    service.threshold_repository = MagicMock()
    return service


def _save_same_measurement(measurement):
    measurement.id = 10
    return measurement


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


def test_normal_heart_rate_is_held_until_average_window_matures():
    service = _service()
    service.threshold_repository.find_by_device_id.return_value = Threshold(
        device_id="band-001",
        heart_rate_min=50,
        heart_rate_max=120,
    )

    with patch("monitoring.application.services.EdgeConfig") as cfg, \
         patch("monitoring.application.services.time.monotonic", return_value=100.0):
        cfg.HEART_RATE_AVERAGE_WINDOW_SECONDS = 300
        cfg.THRESHOLD_SYNC_ENABLED = False
        measurement = service.create_measurement(_device(), heart_rate=72)

    assert measurement.average_pending is True
    assert measurement.averaged is False
    assert measurement.immediate_alert is False
    service.measurement_repository.save.assert_not_called()
    service.cloud_gateway.publish.assert_not_called()


def test_normal_heart_rate_publishes_average_when_window_matures():
    service = _service()
    service.threshold_repository.find_by_device_id.return_value = Threshold(
        device_id="band-001",
        heart_rate_min=50,
        heart_rate_max=120,
    )
    service.measurement_repository.save.side_effect = _save_same_measurement
    service.device_repository.find_by_device_id.return_value = _device()
    service.cloud_gateway.publish.return_value = True

    with patch("monitoring.application.services.EdgeConfig") as cfg, \
         patch("monitoring.application.services.time.monotonic", side_effect=[100.0, 401.0]):
        cfg.HEART_RATE_AVERAGE_WINDOW_SECONDS = 300
        cfg.THRESHOLD_SYNC_ENABLED = False
        cfg.CLOUD_SYNC_ENABLED = True
        cfg.REGISTRY_SYNC_ENABLED = False
        service.create_measurement(_device(), heart_rate=70)
        averaged = service.create_measurement(_device(), heart_rate=80)

    saved_measurement = service.measurement_repository.save.call_args.args[0]
    assert saved_measurement.heart_rate == 75
    assert averaged.averaged is True
    assert averaged.average_pending is False
    assert averaged.immediate_alert is False
    service.cloud_gateway.publish.assert_called_once()


def test_out_of_threshold_heart_rate_is_published_immediately():
    service = _service()
    service.threshold_repository.find_by_device_id.return_value = Threshold(
        device_id="band-001",
        heart_rate_min=50,
        heart_rate_max=120,
    )
    service.measurement_repository.save.side_effect = _save_same_measurement
    service.device_repository.find_by_device_id.return_value = _device()
    service.cloud_gateway.publish.return_value = True

    with patch("monitoring.application.services.EdgeConfig") as cfg:
        cfg.HEART_RATE_AVERAGE_WINDOW_SECONDS = 300
        cfg.THRESHOLD_SYNC_ENABLED = False
        cfg.CLOUD_SYNC_ENABLED = True
        cfg.REGISTRY_SYNC_ENABLED = False
        measurement = service.create_measurement(_device(), heart_rate=130)

    saved_measurement = service.measurement_repository.save.call_args.args[0]
    assert saved_measurement.heart_rate == 130
    assert measurement.immediate_alert is True
    assert measurement.averaged is False
    assert measurement.average_pending is False
    assert "band-001" not in service.heart_rate_windows


def test_threshold_availability_change_resets_pending_average_window():
    service = _service()
    service.threshold_repository.find_by_device_id.side_effect = [
        None,
        Threshold(device_id="band-001", heart_rate_min=60, heart_rate_max=100),
    ]

    with patch("monitoring.application.services.EdgeConfig") as cfg, \
         patch("monitoring.application.services.time.monotonic", side_effect=[100.0, 401.0]):
        cfg.HEART_RATE_AVERAGE_WINDOW_SECONDS = 300
        cfg.THRESHOLD_SYNC_ENABLED = False
        first = service.create_measurement(_device(), heart_rate=130)
        second = service.create_measurement(_device(), heart_rate=80)

    assert first.average_pending is True
    assert second.average_pending is True
    assert service.heart_rate_windows["band-001"].total == 80
    service.measurement_repository.save.assert_not_called()
