"""Tests for the threshold REST endpoints."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from monitoring.domain.entities import Threshold


@pytest.fixture
def client():
    """Flask test client with a minimal app that only registers monitoring_api."""
    from flask import Flask
    from monitoring.interfaces.services import monitoring_api
    app = Flask(__name__)
    app.register_blueprint(monitoring_api)
    app.config["TESTING"] = True
    return app.test_client()


def _make_threshold(**kwargs):
    defaults = dict(
        device_id="band-001",
        heart_rate_min=50,
        heart_rate_max=120,
        systolic_min=None,
        systolic_max=None,
        diastolic_min=None,
        diastolic_max=None,
        temperature_min=35.0,
        temperature_max=38.5,
        oxygen_saturation_min=90,
        oxygen_saturation_max=None,
        respiratory_rate_min=None,
        respiratory_rate_max=None,
        cloud_updated_at=datetime(2026, 6, 29, 10, 0, 0, tzinfo=timezone.utc),
        id=1,
    )
    return Threshold(**{**defaults, **kwargs})


# --- GET /api/v1/monitoring/thresholds ---

def test_get_thresholds_returns_empty_list(client):
    with patch("monitoring.interfaces.services.threshold_repository") as repo:
        repo.find_all.return_value = []
        resp = client.get("/api/v1/monitoring/thresholds")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_thresholds_returns_list_of_records(client):
    t = _make_threshold()
    with patch("monitoring.interfaces.services.threshold_repository") as repo:
        repo.find_all.return_value = [t]
        resp = client.get("/api/v1/monitoring/thresholds")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["device_id"] == "band-001"
    assert data[0]["heart_rate_min"] == 50
    assert data[0]["heart_rate_max"] == 120
    assert data[0]["temperature_min"] == 35.0
    assert data[0]["oxygen_saturation_min"] == 90
    assert data[0]["systolic_min"] is None
    assert "cloud_updated_at" in data[0]


def test_get_thresholds_returns_multiple_records(client):
    t1 = _make_threshold(device_id="band-001", id=1)
    t2 = _make_threshold(device_id="band-002", id=2)
    with patch("monitoring.interfaces.services.threshold_repository") as repo:
        repo.find_all.return_value = [t1, t2]
        resp = client.get("/api/v1/monitoring/thresholds")
    data = resp.get_json()
    assert len(data) == 2
    assert {d["device_id"] for d in data} == {"band-001", "band-002"}


# --- GET /api/v1/monitoring/thresholds/<device_id> ---

def test_get_threshold_by_device_returns_200_when_found(client):
    t = _make_threshold()
    with patch("monitoring.interfaces.services.threshold_repository") as repo:
        repo.find_by_device_id.return_value = t
        resp = client.get("/api/v1/monitoring/thresholds/band-001")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["device_id"] == "band-001"
    assert data["heart_rate_max"] == 120


def test_get_threshold_by_device_returns_404_when_missing(client):
    with patch("monitoring.interfaces.services.threshold_repository") as repo:
        repo.find_by_device_id.return_value = None
        resp = client.get("/api/v1/monitoring/thresholds/nonexistent")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_get_threshold_by_device_passes_device_id_to_repo(client):
    with patch("monitoring.interfaces.services.threshold_repository") as repo:
        repo.find_by_device_id.return_value = None
        client.get("/api/v1/monitoring/thresholds/band-007")
    repo.find_by_device_id.assert_called_once_with("band-007")


# --- POST /api/v1/monitoring/thresholds/sync-from-cloud ---

def test_sync_from_cloud_returns_503_when_disabled(client):
    with patch("monitoring.interfaces.services.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = False
        resp = client.post("/api/v1/monitoring/thresholds/sync-from-cloud")
    assert resp.status_code == 503
    assert "error" in resp.get_json()


def test_sync_from_cloud_returns_503_when_no_gateway_credentials(client):
    with patch("monitoring.interfaces.services.EdgeConfig") as cfg, \
         patch("monitoring.interfaces.services.threshold_sync_service") as svc:
        cfg.THRESHOLD_SYNC_ENABLED = True
        cfg.GATEWAY_DEVICE_ID = "   "
        svc.sync_from_cloud.return_value = 0
        resp = client.post("/api/v1/monitoring/thresholds/sync-from-cloud")
    assert resp.status_code == 503


def test_sync_from_cloud_returns_200_with_applied_count(client):
    with patch("monitoring.interfaces.services.EdgeConfig") as cfg, \
         patch("monitoring.interfaces.services.threshold_sync_service") as svc:
        cfg.THRESHOLD_SYNC_ENABLED = True
        cfg.GATEWAY_DEVICE_ID = "edge-001"
        svc.sync_from_cloud.return_value = 3
        resp = client.post("/api/v1/monitoring/thresholds/sync-from-cloud")
    assert resp.status_code == 200
    assert resp.get_json() == {"applied": 3}


def test_sync_from_cloud_returns_200_with_zero_when_already_up_to_date(client):
    with patch("monitoring.interfaces.services.EdgeConfig") as cfg, \
         patch("monitoring.interfaces.services.threshold_sync_service") as svc:
        cfg.THRESHOLD_SYNC_ENABLED = True
        cfg.GATEWAY_DEVICE_ID = "edge-001"
        svc.sync_from_cloud.return_value = 0
        resp = client.post("/api/v1/monitoring/thresholds/sync-from-cloud")
    assert resp.status_code == 200
    assert resp.get_json()["applied"] == 0
