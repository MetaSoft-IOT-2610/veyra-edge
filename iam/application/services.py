"""Application services for the IAM bounded context.

Application services orchestrate use-cases by coordinating domain objects and
repositories.  They contain no domain logic themselves; all business rules live
in the domain layer.
"""
from typing import List, Optional

from iam.domain.entities import Device
from iam.domain.services import AuthService, DeviceService
from iam.infrastructure.repositories import DeviceRepository


class DeviceApplicationService:
    """Application service that orchestrates device-provisioning use-cases.

    The cloud backend owns the device registry; this use-case applies
    backend-issued node registrations to the local edge registry.
    """

    def __init__(self):
        """Initialise the service with its required collaborators."""
        self.device_repository = DeviceRepository()
        self.device_service = DeviceService()

    def register_device(
            self,
            device_id: str,
            device_type: str,
            api_key: str) -> Device:
        """Register a node pushed by the backend into the edge registry.

        Args:
            device_id (str): Stable node identifier assigned by the backend.
            device_type (str): Device category (``'VITAL_SIGNS'`` or ``'GPS'``).
            api_key (str): Secret API key used for telemetry authentication.

        Returns:
            Device: The persisted device entity with its assigned ``id``.

        Raises:
            ValueError: If the provisioning data is invalid.
            DeviceAlreadyExistsError: If the device is already registered.
        """
        device = self.device_service.create_device(
            device_id, device_type, api_key
        )
        return self.device_repository.save(device)

    def get_all_devices(self) -> List[Device]:
        """Return every device registered at the edge."""
        return self.device_repository.find_all()


class AuthApplicationService:
    """Application service that orchestrates device-authentication use-cases.

    Coordinates the :class:`~iam.infrastructure.repositories.DeviceRepository`
    (reading credentials) and :class:`~iam.domain.services.AuthService`
    (applying the authentication rule) to validate inbound telemetry.
    """

    def __init__(self):
        """Initialise the service with its required collaborators."""
        self.device_repository = DeviceRepository()
        self.auth_service = AuthService()

    def authenticate(self, device_id: str, api_key: str) -> bool:
        """Authenticate a device by its node identifier and API key.

        Args:
            device_id (str): Stable node identifier provided by the device.
            api_key (str): Secret API key from the ``X-API-Key`` header.

        Returns:
            bool: ``True`` if a device with the given credentials exists.
        """
        return self.get_device(device_id, api_key) is not None

    def get_device(self, device_id: str, api_key: str) -> Optional[Device]:
        """Return the registered device for valid gateway credentials."""
        return self.device_repository.find_by_id_and_api_key(device_id, api_key)
