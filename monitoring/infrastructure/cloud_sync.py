"""Cloud synchronization gateway for the Monitoring bounded context.

Acts as an anti-corruption layer between the edge domain model and the cloud
backend's REST contract.  It translates a local
:class:`~monitoring.domain.entities.Measurement` into the JSON payload expected
by the backend Tracking bounded context and publishes it over HTTP.

The gateway is intentionally tolerant: any network or backend failure is
reported as an unsuccessful publish (``False``) rather than raising, so the
calling application service can keep the reading buffered locally and retry it
later without interrupting telemetry ingestion.
"""
import logging

import requests

from monitoring.domain.entities import Measurement
from shared.infrastructure.config import EdgeConfig
from shared.infrastructure.gateway_auth import gateway_cloud_auth_headers

LOGGER = logging.getLogger(__name__)

# Backend endpoint that ingests vital-signs telemetry from the edge.
MEASUREMENTS_PATH = "/api/v1/measurements"


class MeasurementCloudGateway:
    """Publishes buffered measurements to the cloud backend over HTTP."""

    def __init__(self, base_url: str = None, timeout: float = None):
        """Initialise the gateway.

        Args:
            base_url (str, optional): Base URL of the cloud backend.  Defaults
                to :attr:`EdgeConfig.API_SYNC_URL`.
            timeout (float, optional): Request timeout in seconds.  Defaults to
                :attr:`EdgeConfig.CLOUD_SYNC_TIMEOUT`.
        """
        self.base_url = (base_url or EdgeConfig.API_SYNC_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else EdgeConfig.CLOUD_SYNC_TIMEOUT

    def publish(self, measurement: Measurement, mac_address: str) -> bool:
        """Publish a single measurement to the cloud backend.

        Args:
            measurement (Measurement): The reading to publish.
            mac_address (str): Registry MAC for ``measurement.device_id``; the
                cloud validates ``deviceId`` + ``macAddress`` before accepting.

        Returns:
            bool: ``True`` if the backend accepted the reading (2xx response);
            ``False`` on any HTTP error or network failure.
        """
        url = f"{self.base_url}{MEASUREMENTS_PATH}"
        payload = self._to_payload(measurement, mac_address)
        headers = gateway_cloud_auth_headers()
        if headers is None:
            LOGGER.warning(
                "Cloud sync skipped for device %s: set GATEWAY_DEVICE_ID in .env (MAC is auto-detected)",
                measurement.device_id,
            )
            return False
        if not self._has_publishable_vitals(measurement):
            LOGGER.debug(
                "Cloud sync skipped for device %s: no vital signs in buffered reading",
                measurement.device_id,
            )
            return False
        headers["Content-Type"] = "application/json"
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            LOGGER.warning("Cloud sync failed for device %s: %s", measurement.device_id, exc)
            return False

        if response.ok:
            LOGGER.info("Synced measurement for device %s to cloud", measurement.device_id)
            return True

        LOGGER.warning(
            "Cloud rejected measurement for device %s: %s %s",
            measurement.device_id, response.status_code, response.text,
        )
        return False

    @staticmethod
    def _has_publishable_vitals(measurement: Measurement) -> bool:
        """Cloud requires at least one vital sign (ambient counts as temperature)."""
        if measurement.heart_rate is not None:
            return True
        if measurement.oxygen_saturation is not None:
            return True
        if measurement.temperature is not None:
            return True
        return measurement.ambient_temperature is not None

    @staticmethod
    def _to_payload(measurement: Measurement, mac_address: str) -> dict:
        """Translate a measurement into the backend's camelCase JSON contract.

        Identity: ``deviceId``, ``deviceType``, and ``macAddress`` identify the
        IoT node; the cloud accepts the reading only when that pair exists in
        its registry.  An optional ``gateway`` block identifies the edge server.
        """
        timestamp = measurement.timestamp
        payload = {
            "deviceId": measurement.device_id,
            "deviceType": measurement.device_type,
            "macAddress": mac_address,
            "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp,
            "heartRate": measurement.heart_rate,
            "temperature": measurement.temperature,
            "oxygenSaturation": measurement.oxygen_saturation,
            "respiratoryRate": measurement.respiratory_rate,
        }
        if measurement.ambient_temperature is not None:
            payload["ambientTemperature"] = measurement.ambient_temperature
        gateway_id = EdgeConfig.GATEWAY_DEVICE_ID.strip()
        if gateway_id:
            payload["gateway"] = {
                "deviceId": gateway_id,
                "deviceType": EdgeConfig.GATEWAY_DEVICE_TYPE,
            }
        if measurement.latitude is not None and measurement.longitude is not None:
            payload["location"] = {
                "latitude": measurement.latitude,
                "longitude": measurement.longitude,
            }
        if measurement.satellite_count is not None:
            payload["satelliteCount"] = measurement.satellite_count
        if measurement.satellites_in_view is not None:
            payload["satellitesInView"] = measurement.satellites_in_view
        if measurement.diagnostics is not None:
            payload["diagnostics"] = measurement.diagnostics
        if measurement.systolic is not None and measurement.diastolic is not None:
            payload["bloodPressure"] = {
                "systolic": measurement.systolic,
                "diastolic": measurement.diastolic,
            }
        return payload
