"""Tests for measurement cloud synchronization."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import requests

from monitoring.domain.entities import Measurement
from monitoring.infrastructure.cloud_sync import MeasurementCloudGateway

BASE_URL = "http://cloud.test/api/v1"
AUTH_HEADERS = {"X-Device-Id": "edge-001", "X-Device-Mac": "AA:BB:CC:DD:EE:FF"}


def _measurement(**overrides):
    defaults = dict(
        device_id="band-001",
        device_type="VITAL_SIGNS",
        timestamp=datetime(2026, 6, 16, 23, 23, tzinfo=timezone.utc),
        heart_rate=72,
    )
    return Measurement(**{**defaults, **overrides})


def _response(ok=True, status_code=200, text=""):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.text = text
    return resp


def test_publish_returns_false_when_gateway_credentials_are_missing():
    gateway = MeasurementCloudGateway(base_url=BASE_URL, timeout=3)
    with patch("monitoring.infrastructure.cloud_sync.gateway_cloud_auth_headers", return_value=None):
        assert gateway.publish(_measurement(), "AA:BB:CC:DD:EE:FF") is False


def test_publish_returns_false_when_measurement_has_no_publishable_data():
    gateway = MeasurementCloudGateway(base_url=BASE_URL, timeout=3)
    measurement = _measurement(heart_rate=None)

    with patch("monitoring.infrastructure.cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.post") as post:
        assert gateway.publish(measurement, "AA:BB:CC:DD:EE:FF") is False

    post.assert_not_called()


def test_publish_treats_location_as_publishable_data():
    gateway = MeasurementCloudGateway(base_url=BASE_URL, timeout=3)
    measurement = _measurement(heart_rate=None, device_type="GPS", latitude=-12.0464, longitude=-77.0428)

    with patch("monitoring.infrastructure.cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.post", return_value=_response()) as post:
        assert gateway.publish(measurement, "AA:BB:CC:DD:EE:FF") is True

    payload = post.call_args.kwargs["json"]
    assert payload["location"] == {"latitude": -12.0464, "longitude": -77.0428}


def test_publish_treats_blood_pressure_as_publishable_vital():
    gateway = MeasurementCloudGateway(base_url=BASE_URL, timeout=3)
    measurement = _measurement(heart_rate=None, systolic=120, diastolic=80)

    with patch("monitoring.infrastructure.cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.post", return_value=_response()) as post:
        assert gateway.publish(measurement, "AA:BB:CC:DD:EE:FF") is True

    payload = post.call_args.kwargs["json"]
    assert payload["bloodPressure"] == {"systolic": 120, "diastolic": 80}


def test_publish_returns_false_on_network_error():
    gateway = MeasurementCloudGateway(base_url=BASE_URL, timeout=3)

    with patch("monitoring.infrastructure.cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.post", side_effect=requests.Timeout("slow cloud")):
        assert gateway.publish(_measurement(), "AA:BB:CC:DD:EE:FF") is False


def test_publish_returns_false_on_rejected_response():
    gateway = MeasurementCloudGateway(base_url=BASE_URL, timeout=3)

    with patch("monitoring.infrastructure.cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.post", return_value=_response(ok=False, status_code=401, text="Unauthorized")):
        assert gateway.publish(_measurement(), "AA:BB:CC:DD:EE:FF") is False


def test_publish_sends_headers_without_mutating_auth_header_source():
    gateway = MeasurementCloudGateway(base_url=BASE_URL, timeout=3)
    headers = dict(AUTH_HEADERS)

    with patch("monitoring.infrastructure.cloud_sync.gateway_cloud_auth_headers", return_value=headers), \
         patch("requests.post", return_value=_response()) as post:
        gateway.publish(_measurement(), "AA:BB:CC:DD:EE:FF")

    assert "Content-Type" not in headers
    assert post.call_args.kwargs["headers"]["Content-Type"] == "application/json"
