"""Domain exceptions for the IAM bounded context.

These exceptions express violations of IAM business rules in domain terms,
allowing the interface layer to translate them into the appropriate HTTP
status codes without leaking persistence or framework details.
"""


class DeviceAlreadyExistsError(Exception):
    """Raised when registering a device whose identity already exists.

    Signals a conflict against the uniqueness invariant of either
    ``device_id`` or ``mac_address`` within the edge device registry.
    """


class DeviceNotFoundError(Exception):
    """Raised when an operation targets a device that is not registered."""
