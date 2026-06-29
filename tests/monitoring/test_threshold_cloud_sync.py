"""Tests for ThresholdCloudGateway."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from monitoring.infrastructure.threshold_cloud_sync import ThresholdCloudGateway

BASE_URL = "http://cloud.test/api/v1"
AUTH_HEADERS = {"X-Device-Id": "edge-001", "X-Device-Mac": "AA:BB:CC:DD:EE:FF"}


@pytest.fixture
def gateway():
    return ThresholdCloudGateway(base_url=BASE_URL, timeout=3)


def _mock_response(ok=True, json_body=None, status_code=200, text=""):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_body or {}
    return resp


# --- pull() ---

def test_pull_returns_none_when_no_credentials(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=None):
        assert gateway.pull(since=None) is None


def test_pull_returns_none_on_network_error(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", side_effect=requests.ConnectionError("unreachable")):
        assert gateway.pull(since=None) is None


def test_pull_returns_none_on_non_ok_response(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(ok=False, status_code=401, text="Unauthorized")):
        assert gateway.pull(since=None) is None


def test_pull_returns_none_when_thresholds_key_missing(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(json_body={"data": []})):
        assert gateway.pull(since=None) is None


def test_pull_returns_none_when_thresholds_not_a_list(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(json_body={"thresholds": "bad"})):
        assert gateway.pull(since=None) is None


def test_pull_returns_list_on_success(gateway):
    entries = [{"device_id": "band-001", "heart_rate_max": 120}]
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(json_body={"thresholds": entries})):
        result = gateway.pull(since=None)
    assert result == entries


def test_pull_returns_empty_list_on_success(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(json_body={"thresholds": []})):
        assert gateway.pull(since=None) == []


def test_pull_sends_since_param_when_provided(gateway):
    since = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(json_body={"thresholds": []})) as mock_get:
        gateway.pull(since=since)
    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs["params"]["since"] == since.isoformat()


def test_pull_omits_since_param_when_none(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(json_body={"thresholds": []})) as mock_get:
        gateway.pull(since=None)
    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs["params"] == {}


def test_pull_hits_correct_url(gateway):
    with patch("monitoring.infrastructure.threshold_cloud_sync.gateway_cloud_auth_headers", return_value=AUTH_HEADERS), \
         patch("requests.get", return_value=_mock_response(json_body={"thresholds": []})) as mock_get:
        gateway.pull(since=None)
    url = mock_get.call_args.args[0]
    assert url == f"{BASE_URL}/edge/thresholds"


# --- parse_cloud_updated_at() ---

def test_parse_cloud_updated_at_with_timezone():
    result = ThresholdCloudGateway.parse_cloud_updated_at("2026-06-29T10:00:00Z")
    assert result.tzinfo is not None
    assert result.year == 2026 and result.month == 6 and result.day == 29


def test_parse_cloud_updated_at_naive_gets_utc():
    result = ThresholdCloudGateway.parse_cloud_updated_at("2026-06-29T10:00:00")
    assert result.tzinfo == timezone.utc


def test_parse_cloud_updated_at_returns_none_on_empty_string():
    assert ThresholdCloudGateway.parse_cloud_updated_at("") is None


def test_parse_cloud_updated_at_returns_none_on_none():
    assert ThresholdCloudGateway.parse_cloud_updated_at(None) is None


def test_parse_cloud_updated_at_returns_none_on_invalid():
    assert ThresholdCloudGateway.parse_cloud_updated_at("not-a-date") is None
