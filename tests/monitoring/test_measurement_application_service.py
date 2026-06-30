"""Tests for MeasurementApplicationService conditional sync logic."""
from unittest.mock import MagicMock
from datetime import datetime, timezone
import pytest

from monitoring.application.services import MeasurementApplicationService
from monitoring.domain.entities import Measurement, Threshold
from iam.domain.entities import Device


def test_create_measurement_syncs_immediately_on_violation():
    # Setup Mocks
    service = MeasurementApplicationService.__new__(MeasurementApplicationService)
    service.measurement_service = MagicMock()
    service.measurement_repository = MagicMock()
    service.threshold_repository = MagicMock()
    service._try_sync = MagicMock()

    device = Device(
        device_id="band-001",
        mac_address="00:11:22:33:44:55",
        device_type="VITAL_SIGNS",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    measurement = Measurement(
        device_id="band-001",
        device_type="VITAL_SIGNS",
        timestamp=datetime.now(timezone.utc),
        heart_rate=120
    )
    service.measurement_service.create_measurement.return_value = measurement
    service.measurement_repository.save.return_value = measurement

    # Threshold violated (heart rate max is 100, measurement has 120)
    threshold = Threshold(device_id="band-001", heart_rate_max=100)
    service.threshold_repository.find_by_device_id.return_value = threshold

    service.create_measurement(device, heart_rate=120)

    service.measurement_repository.save.assert_called_once_with(measurement)
    service._try_sync.assert_called_once_with(measurement, sync_registry=True)


def test_create_measurement_does_not_sync_immediately_on_no_violation():
    # Setup Mocks
    service = MeasurementApplicationService.__new__(MeasurementApplicationService)
    service.measurement_service = MagicMock()
    service.measurement_repository = MagicMock()
    service.threshold_repository = MagicMock()
    service._try_sync = MagicMock()

    device = Device(
        device_id="band-001",
        mac_address="00:11:22:33:44:55",
        device_type="VITAL_SIGNS",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    measurement = Measurement(
        device_id="band-001",
        device_type="VITAL_SIGNS",
        timestamp=datetime.now(timezone.utc),
        heart_rate=80
    )
    service.measurement_service.create_measurement.return_value = measurement
    service.measurement_repository.save.return_value = measurement

    # Within threshold (heart rate max is 100, measurement has 80)
    threshold = Threshold(device_id="band-001", heart_rate_max=100)
    service.threshold_repository.find_by_device_id.return_value = threshold

    service.create_measurement(device, heart_rate=80)

    service.measurement_repository.save.assert_called_once_with(measurement)
    service._try_sync.assert_not_called()


def test_create_measurement_does_not_sync_immediately_if_no_threshold_record():
    # Setup Mocks
    service = MeasurementApplicationService.__new__(MeasurementApplicationService)
    service.measurement_service = MagicMock()
    service.measurement_repository = MagicMock()
    service.threshold_repository = MagicMock()
    service._try_sync = MagicMock()

    device = Device(
        device_id="band-001",
        mac_address="00:11:22:33:44:55",
        device_type="VITAL_SIGNS",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    measurement = Measurement(
        device_id="band-001",
        device_type="VITAL_SIGNS",
        timestamp=datetime.now(timezone.utc),
        heart_rate=80
    )
    service.measurement_service.create_measurement.return_value = measurement
    service.measurement_repository.save.return_value = measurement

    # No threshold record
    service.threshold_repository.find_by_device_id.return_value = None

    service.create_measurement(device, heart_rate=80)

    service.measurement_repository.save.assert_called_once_with(measurement)
    service._try_sync.assert_not_called()
