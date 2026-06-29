"""Repository implementation for vital-sign thresholds."""
from datetime import datetime, timezone
from typing import Any, List, Optional

import peewee

from monitoring.domain.entities import Threshold
from monitoring.infrastructure.models import Threshold as ThresholdModel
from monitoring.infrastructure.threshold_cloud_sync import ThresholdCloudGateway


class ThresholdRepository:
    """Persists and reconstructs :class:`~monitoring.domain.entities.Threshold` entities."""

    @staticmethod
    def _to_entity(model: ThresholdModel) -> Threshold:
        return Threshold(
            device_id=model.device_id,
            heart_rate_min=model.heart_rate_min,
            heart_rate_max=model.heart_rate_max,
            systolic_min=model.systolic_min,
            systolic_max=model.systolic_max,
            diastolic_min=model.diastolic_min,
            diastolic_max=model.diastolic_max,
            temperature_min=model.temperature_min,
            temperature_max=model.temperature_max,
            oxygen_saturation_min=model.oxygen_saturation_min,
            oxygen_saturation_max=model.oxygen_saturation_max,
            respiratory_rate_min=model.respiratory_rate_min,
            respiratory_rate_max=model.respiratory_rate_max,
            cloud_updated_at=model.cloud_updated_at,
            id=model.id,
        )

    @staticmethod
    def find_by_device_id(device_id: str) -> Optional[Threshold]:
        try:
            model = ThresholdModel.get(ThresholdModel.device_id == device_id)
            return ThresholdRepository._to_entity(model)
        except peewee.DoesNotExist:
            return None

    @staticmethod
    def find_all() -> List[Threshold]:
        return [ThresholdRepository._to_entity(m) for m in ThresholdModel.select()]

    @staticmethod
    def get_max_cloud_updated_at() -> Optional[datetime]:
        value = ThresholdModel.select(peewee.fn.MAX(ThresholdModel.cloud_updated_at)).scalar()
        return value

    @staticmethod
    def upsert_from_cloud(entry: dict[str, Any]) -> bool:
        """Create or update a threshold row from a cloud payload entry."""
        device_id = str(entry["device_id"]).strip()
        cloud_updated_at = ThresholdCloudGateway.parse_cloud_updated_at(
            entry.get("updated_at") or entry.get("cloud_updated_at")
        )
        now = datetime.now(timezone.utc)

        def _int(key):
            v = entry.get(key)
            return int(v) if v is not None else None

        def _float(key):
            v = entry.get(key)
            return float(v) if v is not None else None

        fields = dict(
            heart_rate_min=_int("heart_rate_min"),
            heart_rate_max=_int("heart_rate_max"),
            systolic_min=_int("systolic_min"),
            systolic_max=_int("systolic_max"),
            diastolic_min=_int("diastolic_min"),
            diastolic_max=_int("diastolic_max"),
            temperature_min=_float("temperature_min"),
            temperature_max=_float("temperature_max"),
            oxygen_saturation_min=_int("oxygen_saturation_min"),
            oxygen_saturation_max=_int("oxygen_saturation_max"),
            respiratory_rate_min=_int("respiratory_rate_min"),
            respiratory_rate_max=_int("respiratory_rate_max"),
            cloud_updated_at=cloud_updated_at,
        )

        try:
            model = ThresholdModel.get(ThresholdModel.device_id == device_id)
        except peewee.DoesNotExist:
            ThresholdModel.create(device_id=device_id, updated_at=now, **fields)
            return True

        changed = any(getattr(model, k) != v for k, v in fields.items())
        if not changed:
            return False

        for k, v in fields.items():
            setattr(model, k, v)
        model.updated_at = now
        model.save()
        return True
