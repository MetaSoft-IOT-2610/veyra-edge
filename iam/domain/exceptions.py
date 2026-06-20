"""Domain exceptions for the IAM bounded context.

These exceptions express violations of IAM business rules in domain terms,
allowing the interface layer to translate them into the appropriate HTTP
status codes without leaking persistence or framework details.
"""


class DeviceAlreadyExistsError(Exception):
    """Raised when registering a device whose ``device_id`` already exists."""


class DeviceNotFoundError(Exception):
    """Raised when an operation targets a device that is not registered."""
