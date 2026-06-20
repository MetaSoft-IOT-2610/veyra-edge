"""Interface (REST API) layer for the IAM bounded context.

Exposes a Flask Blueprint (``iam_api``) that lets the cloud backend provision
the edge device registry, and shared authentication helpers used by other
bounded contexts to guard telemetry ingestion.
"""
from flask import Blueprint, request, jsonify
import logging

from iam.application.registry_sync_service import DeviceRegistrySyncApplicationService
from iam.application.services import AuthApplicationService, DeviceApplicationService
from iam.domain.entities import Device
from iam.domain.exceptions import DeviceAlreadyExistsError
from shared.infrastructure.config import EdgeConfig

iam_api = Blueprint("iam_api", __name__)
logger = logging.getLogger(__name__)

device_service = DeviceApplicationService()
auth_service = AuthApplicationService()
registry_sync_service = DeviceRegistrySyncApplicationService()


def _device_to_json(device: Device) -> dict:
    """Serialise a :class:`~iam.domain.entities.Device` entity to a JSON dict."""
    return {
        "id": device.id,
        "device_id": device.device_id,
        "device_type": device.device_type,
        "mac_address": device.mac_address,
        "status": device.status,
        "cloud_updated_at": (
            device.cloud_updated_at.isoformat()
            if device.cloud_updated_at and hasattr(device.cloud_updated_at, "isoformat")
            else device.cloud_updated_at
        ),
        "created_at": device.created_at.isoformat() if hasattr(device.created_at, "isoformat") else device.created_at,
        "updated_at": device.updated_at.isoformat() if hasattr(device.updated_at, "isoformat") else device.updated_at,
    }


def _read_device_id() -> str | None:
    """Read the node identifier from ``X-Device-Id`` or the JSON body."""
    device_id = request.headers.get("X-Device-Id")
    if device_id:
        return device_id.strip()
    if request.json and request.json.get("device_id"):
        return str(request.json.get("device_id")).strip()
    return None


def _read_mac_address() -> str | None:
    """Read the MAC address from ``X-Device-Mac`` or the JSON body."""
    mac_address = request.headers.get("X-Device-Mac")
    if mac_address:
        return mac_address.strip()
    if request.json and request.json.get("mac_address"):
        return str(request.json.get("mac_address")).strip()
    return None


def _read_bearer_token() -> str | None:
    """Read a Bearer access token from the ``Authorization`` header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def resolve_authenticated_device():
    """Return the IAM device for the current telemetry request.

    Telemetry must include ``Authorization: Bearer <token>`` obtained from
    :func:`sign_in`.
    """
    token = _read_bearer_token()
    if not token:
        logger.warning("Telemetry auth failed: missing Bearer access token")
        return None, (jsonify({"error": "Missing or invalid Authorization Bearer token"}), 401)

    device = auth_service.get_device_from_token(token)
    if not device:
        logger.warning("Telemetry auth failed: invalid or expired access token")
        return None, (jsonify({"error": "Invalid or expired access token"}), 401)
    return device, None


@iam_api.route("/api/v1/auth/sign-in", methods=["POST"])
def sign_in():
    """Authenticate a device and issue a short-lived access token.

    **Headers:** ``X-Device-Id``, ``X-Device-Mac``

    **Responses:**

    - ``200 OK`` – Sign-in succeeded; response includes ``access_token``.
    - ``401 Unauthorized`` – Missing or invalid credentials; no token is returned.
    - ``503 Service Unavailable`` – Token signing is not configured on the edge.
    """
    device_id = _read_device_id()
    mac_address = _read_mac_address()
    if not device_id or not mac_address:
        return jsonify({"error": "Missing X-Device-Id or X-Device-Mac"}), 401

    if not EdgeConfig.EDGE_JWT_SECRET.strip():
        logger.error("Device sign-in rejected: EDGE_JWT_SECRET is not configured")
        return jsonify({"error": "Token signing is not configured on the edge server"}), 503

    token_payload = auth_service.sign_in(device_id, mac_address)
    if not token_payload:
        logger.warning("Device sign-in failed for device_id=%s", device_id)
        return jsonify({"error": "Invalid device_id or MAC address"}), 401

    logger.info("Device sign-in succeeded for device_id=%s", device_id)
    return jsonify(token_payload), 200


@iam_api.route("/api/v1/devices", methods=["POST"])
def register_device():
    """Register a node provisioned by the cloud backend.

    **Request body (JSON):**

    .. code-block:: json

        {
            "device_id": "band-001",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "device_type": "VITAL_SIGNS"
        }
    """
    data = request.json or {}
    try:
        device = device_service.register_device(
            device_id=data["device_id"],
            device_type=data["device_type"],
            mac_address=data["mac_address"],
        )
        return jsonify(_device_to_json(device)), 201
    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except DeviceAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@iam_api.route("/api/v1/devices/sync-from-cloud", methods=["POST"])
def sync_devices_from_cloud():
    """Pull the latest device registry from the cloud (manual / observability).

    Requires ``REGISTRY_SYNC_ENABLED=true`` and valid gateway credentials in ``.env``.
    """
    if not EdgeConfig.REGISTRY_SYNC_ENABLED:
        return jsonify({"error": "Registry sync is disabled on this edge server"}), 503

    applied = registry_sync_service.sync_from_cloud()
    if applied == 0 and not EdgeConfig.GATEWAY_DEVICE_ID.strip():
        return jsonify({"error": "Gateway credentials are not configured"}), 503

    return jsonify({"applied": applied}), 200


@iam_api.route("/api/v1/devices", methods=["GET"])
def get_all_devices():
    """List every device registered at the edge (observability helper)."""
    devices = device_service.get_all_devices()
    return jsonify([_device_to_json(d) for d in devices]), 200
