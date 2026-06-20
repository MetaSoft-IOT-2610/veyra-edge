"""Application services for the IAM bounded context.

Application services orchestrate use-cases by coordinating domain objects and
repositories.  They contain no domain logic themselves; all business rules live
in the domain layer.
"""
from typing import List, Optional

from iam.domain.entities import Device
from iam.domain.services import AuthService, DeviceService
from iam.infrastructure.repositories import DeviceRepository
from iam.infrastructure.token_service import TokenService
from shared.infrastructure.config import EdgeConfig


class DeviceApplicationService:
    """Application service that orchestrates device-provisioning use-cases."""

    def __init__(self):
        """Initialise the service with its required collaborators."""
        self.device_repository = DeviceRepository()
        self.device_service = DeviceService()

    def register_device(
            self,
            device_id: str,
            device_type: str,
            mac_address: str) -> Device:
        """Register a node pushed by the backend into the edge registry."""
        device = self.device_service.create_device(
            device_id, device_type, mac_address
        )
        return self.device_repository.save(device)

    def get_all_devices(self) -> List[Device]:
        """Return every device registered at the edge."""
        return self.device_repository.find_all()


class AuthApplicationService:
    """Application service that orchestrates device-authentication use-cases."""

    def __init__(self):
        """Initialise the service with its required collaborators."""
        self.device_repository = DeviceRepository()
        self.auth_service = AuthService()

    def authenticate(self, device_id: str, mac_address: str) -> bool:
        """Authenticate a device by its node identifier and MAC address."""
        return self.get_device(device_id, mac_address) is not None

    def get_device(self, device_id: str, mac_address: str) -> Optional[Device]:
        """Return the registered device for valid sign-in credentials."""
        return self.device_repository.find_by_id_and_mac_address(device_id, mac_address)

    def sign_in(self, device_id: str, mac_address: str) -> Optional[dict]:
        """Authenticate a device and issue a short-lived access token."""
        device = self.get_device(device_id, mac_address)
        if not device or not self.auth_service.authenticate(device):
            return None

        secret = EdgeConfig.EDGE_JWT_SECRET.strip()
        if not secret:
            return None

        access_token, expires_in = TokenService.create_access_token(
            device.device_id,
            secret,
            EdgeConfig.EDGE_JWT_TTL_SECONDS,
        )
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }

    def get_device_from_token(self, token: str) -> Optional[Device]:
        """Resolve a registered device from a Bearer access token."""
        secret = EdgeConfig.EDGE_JWT_SECRET.strip()
        if not secret:
            return None

        device_id = TokenService.decode_access_token(token, secret)
        if not device_id:
            return None

        return self.device_repository.find_by_device_id(device_id)
