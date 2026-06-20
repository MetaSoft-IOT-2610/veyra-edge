"""Interface (REST API) layer for the IAM bounded context.

Exposes a Flask Blueprint (``iam_api``) that lets the cloud backend provision
the edge device registry, and a shared authentication helper
(``authenticate_request``) used by other bounded contexts to guard telemetry
ingestion.  This layer owns no domain logic; it handles HTTP request/response
concerns and delegates to the application services.
"""
from flask import Blueprint, request, jsonify
import logging

from iam.application.services import AuthApplicationService, DeviceApplicationService
from iam.domain.entities import Device
from iam.domain.exceptions import DeviceAlreadyExistsError

iam_api = Blueprint("iam_api", __name__)
logger = logging.getLogger(__name__)

# Module-level singletons — instantiated once per worker process.
device_service = DeviceApplicationService()
auth_service = AuthApplicationService()


def _device_to_json(device: Device) -> dict:
    """Serialise a :class:`~iam.domain.entities.Device` entity to a JSON dict."""
    return {
        "id": device.id,
        "device_id": device.device_id,
        "device_type": device.device_type,
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


def authenticate_request():
    """Validate the device identity for an incoming telemetry request.

    Reads ``X-Device-Id`` (preferred) or ``device_id`` in the JSON body, plus
    ``X-API-Key``, and verifies the pair against the edge device registry.

    Returns:
        tuple[flask.Response, int] | None: ``(JSON, 401)`` on failure; ``None`` if ok.
    """
    device_id = _read_device_id()
    api_key = request.headers.get("X-API-Key")
    if not device_id or not api_key:
        return jsonify({"error": "Missing X-Device-Id (or device_id) or X-API-Key"}), 401
    if not auth_service.authenticate(device_id, api_key):
        return jsonify({"error": "Invalid device_id or API key"}), 401
    return None


def resolve_authenticated_device():
    """Return the IAM device for the current telemetry request.

    Call after :func:`authenticate_request` succeeds (or call directly and
    handle errors).  The returned :class:`~iam.domain.entities.Device` is the
    gateway's source of truth for cloud identity (``device_type``, etc.).

    Returns:
        tuple[Device | None, tuple | None]: ``(device, None)`` on success;
        ``(None, error_response)`` when credentials are missing or invalid.
    """
    device_id = _read_device_id()
    api_key = request.headers.get("X-API-Key")
    if not device_id or not api_key:
        logger.warning(
            "Telemetry auth failed: missing credentials (device_id=%s, has_api_key=%s)",
            device_id or "—",
            bool(api_key),
        )
        return None, (jsonify({"error": "Missing X-Device-Id (or device_id) or X-API-Key"}), 401)
    device = auth_service.get_device(device_id, api_key)
    if not device:
        logger.warning("Telemetry auth failed: invalid credentials for device_id=%s", device_id)
        return None, (jsonify({"error": "Invalid device_id or API key"}), 401)
    return device, None


@iam_api.route("/api/v1/devices", methods=["POST"])
def register_device():
    """Register a node provisioned by the cloud backend.

    Gateway identification uses ``device_id`` + ``api_key`` only.

    **Request body (JSON):**

    .. code-block:: json

        {
            "device_id": "band-001",
            "api_key": "s3cr3t-key",
            "device_type": "VITAL_SIGNS"
        }

    **Responses:**

    - ``201 Created`` – Device registered successfully.
    - ``400 Bad Request`` – Missing or invalid fields.
    - ``409 Conflict`` – A device with the same ``device_id`` already exists.
    """
    data = request.json or {}
    try:
        device = device_service.register_device(
            device_id=data["device_id"],
            device_type=data["device_type"],
            api_key=data["api_key"],
        )
        return jsonify(_device_to_json(device)), 201
    except KeyError:
        return jsonify({"error": "Missing required fields"}), 400
    except DeviceAlreadyExistsError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@iam_api.route("/api/v1/devices", methods=["GET"])
def get_all_devices():
    """List every device registered at the edge (observability helper)."""
    devices = device_service.get_all_devices()
    return jsonify([_device_to_json(d) for d in devices]), 200
