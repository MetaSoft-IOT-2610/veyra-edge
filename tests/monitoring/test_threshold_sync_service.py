"""Tests for ThresholdSyncApplicationService."""
from unittest.mock import MagicMock, patch

from monitoring.application.threshold_sync_service import ThresholdSyncApplicationService

_VALID_ENTRY = {
    "device_id": "band-001",
    "heart_rate_min": 50,
    "heart_rate_max": 120,
    "updated_at": "2026-06-29T10:00:00Z",
}


def _make_service(gateway_entries, max_ts=None, upsert_returns=True):
    """Build a service with all dependencies mocked."""
    service = ThresholdSyncApplicationService.__new__(ThresholdSyncApplicationService)
    service.threshold_repository = MagicMock()
    service.threshold_gateway = MagicMock()
    service.threshold_repository.get_max_cloud_updated_at.return_value = max_ts
    service.threshold_gateway.pull.return_value = gateway_entries
    service.threshold_repository.upsert_from_cloud.return_value = upsert_returns
    return service


def test_sync_returns_zero_when_disabled():
    service = _make_service([_VALID_ENTRY])
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = False
        result = service.sync_from_cloud()
    assert result == 0
    service.threshold_gateway.pull.assert_not_called()


def test_sync_returns_zero_when_cloud_unreachable():
    service = _make_service(gateway_entries=None)
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        result = service.sync_from_cloud()
    assert result == 0


def test_sync_applies_valid_entries():
    service = _make_service([_VALID_ENTRY, {**_VALID_ENTRY, "device_id": "band-002"}])
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        result = service.sync_from_cloud()
    assert result == 2
    assert service.threshold_repository.upsert_from_cloud.call_count == 2


def test_sync_returns_zero_when_cloud_returns_empty_list():
    service = _make_service([])
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        result = service.sync_from_cloud()
    assert result == 0


def test_sync_skips_non_dict_entries():
    service = _make_service(["bad", None, _VALID_ENTRY])
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        result = service.sync_from_cloud()
    assert result == 1


def test_sync_skips_entry_that_raises_value_error():
    service = _make_service([_VALID_ENTRY])
    service.threshold_repository.upsert_from_cloud.side_effect = ValueError("bad entry")
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        result = service.sync_from_cloud()
    assert result == 0


def test_sync_skips_entry_that_raises_key_error():
    service = _make_service([_VALID_ENTRY])
    service.threshold_repository.upsert_from_cloud.side_effect = KeyError("device_id")
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        result = service.sync_from_cloud()
    assert result == 0


def test_sync_counts_only_upserted_entries():
    service = _make_service([_VALID_ENTRY, {**_VALID_ENTRY, "device_id": "band-002"}])
    service.threshold_repository.upsert_from_cloud.side_effect = [True, False]
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        result = service.sync_from_cloud()
    assert result == 1


def test_sync_passes_since_to_gateway():
    from datetime import datetime, timezone
    since = datetime(2026, 6, 1, tzinfo=timezone.utc)
    service = _make_service([], max_ts=since)
    with patch("monitoring.application.threshold_sync_service.EdgeConfig") as cfg:
        cfg.THRESHOLD_SYNC_ENABLED = True
        service.sync_from_cloud()
    service.threshold_gateway.pull.assert_called_once_with(since)
