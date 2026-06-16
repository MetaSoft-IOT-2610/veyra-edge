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

    def publish(self, measurement: Measurement) -> bool:
        """Publish a single measurement to the cloud backend.

        Args:
            measurement (Measurement): The reading to publish.

        Returns:
            bool: ``True`` if the backend accepted the reading (2xx response);
            ``False`` on any HTTP error or network failure.
        """
        url = f"{self.base_url}{MEASUREMENTS_PATH}"
        payload = self._to_payload(measurement)
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            LOGGER.warning("Cloud sync failed for device %s: %s", measurement.mac_address, exc)
            return False

        if response.ok:
            LOGGER.info("Synced measurement for device %s to cloud", measurement.mac_address)
            return True

        LOGGER.warning(
            "Cloud rejected measurement for device %s: %s %s",
            measurement.mac_address, response.status_code, response.text,
        )
        return False

    @staticmethod
    def _to_payload(measurement: Measurement) -> dict:
        """Translate a measurement into the backend's camelCase JSON contract.

        Blood pressure is nested to match the backend ``BloodPressure`` value
        object and is omitted entirely when not reported.
        """
        timestamp = measurement.timestamp
        payload = {
            "deviceId": measurement.mac_address,
            "nursingHomeId": measurement.nursing_home_id,
            "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp,
            "heartRate": measurement.heart_rate,
            "temperature": measurement.temperature,
            "oxygenSaturation": measurement.oxygen_saturation,
            "respiratoryRate": measurement.respiratory_rate,
        }
        if measurement.systolic is not None and measurement.diastolic is not None:
            payload["bloodPressure"] = {
                "systolic": measurement.systolic,
                "diastolic": measurement.diastolic,
            }
        return payload
