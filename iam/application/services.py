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

    The cloud backend owns the device registry; these use-cases apply the
    backend-issued provisioning commands (register a device, correct a MAC
    address) to the local edge registry.
    """

    def __init__(self):
        """Initialise the service with its required collaborators."""
        self.device_repository = DeviceRepository()
        self.device_service = DeviceService()

    def register_device(
            self,
            device_id: str,
            mac_address: str,
            nursing_home_id: int,
            device_type: str,
            api_key: str) -> Device:
        """Register a device pushed by the backend into the edge registry.

        Args:
            device_id (str): Stable identifier assigned by the backend.
            mac_address (str): Hardware MAC address of the device.
            nursing_home_id (int): Owning nursing-home identifier.
            device_type (str): Device category (``'VITAL_SIGNS'`` or ``'GPS'``).
            api_key (str): Secret API key used for telemetry authentication.

        Returns:
            Device: The persisted device entity with its assigned ``id``.

        Raises:
            ValueError: If the provisioning data is invalid.
            DeviceAlreadyExistsError: If the device is already registered.
        """
        device = self.device_service.create_device(
            device_id, mac_address, nursing_home_id, device_type, api_key
        )
        return self.device_repository.save(device)

    def update_mac_address(self, device_id: str, mac_address: str) -> Device:
        """Apply a backend-issued MAC-address correction to a device.

        Args:
            device_id (str): Stable backend identifier of the device.
            mac_address (str): The corrected hardware MAC address.

        Returns:
            Device: The updated device entity.

        Raises:
            ValueError: If ``mac_address`` is empty.
            DeviceNotFoundError: If the device is not registered.
            DeviceAlreadyExistsError: If the MAC address is already in use.
        """
        if not mac_address or not str(mac_address).strip():
            raise ValueError("mac_address cannot be empty")
        return self.device_repository.update_mac_address(device_id, str(mac_address).strip())

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

    def authenticate_device(self, mac_address: str, api_key: str) -> bool:
        """Authenticate a device by its MAC address and API key.

        Args:
            mac_address (str): Hardware MAC address provided by the device.
            api_key (str): Secret API key from the ``X-API-Key`` header.

        Returns:
            bool: ``True`` if a device with the given credentials exists.
        """
        device: Optional[Device] = self.device_repository.find_by_mac_and_api_key(mac_address, api_key)
        return self.auth_service.authenticate(device)
