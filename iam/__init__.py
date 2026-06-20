"""Identity and Access Management (IAM) bounded context package.

Handles device provisioning, look-up, and API-key-based authentication for
IoT devices at the edge, following a Domain-Driven Design layered architecture:

- **domain**: ``Device`` aggregate root, ``DeviceService`` and ``AuthService``
  domain services.
- **application**: ``DeviceApplicationService`` and ``AuthApplicationService``
  that orchestrate provisioning and authentication use-cases.
- **infrastructure**: Peewee ORM models and repository implementations for
  persisting device data.
- **interfaces**: Flask Blueprint exposing device-provisioning endpoints and
  authentication helpers used by other bounded contexts.
"""
