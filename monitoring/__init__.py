"""Monitoring bounded context package.

Provides vital-signs telemetry ingestion, local buffering, and cloud
synchronization following the Domain-Driven Design (DDD) approach, structured
into domain, application, infrastructure, and interface layers.

- **domain**: Core entities (``Measurement``) and domain services that
  encapsulate vital-signs validation rules.
- **application**: Orchestrates use-cases by coordinating domain services
  with infrastructure repositories and the cloud-sync gateway.
- **infrastructure**: Peewee ORM models, repository implementations, and the
  cloud-sync anti-corruption layer.
- **interfaces**: Flask Blueprint exposing the REST API endpoints for this
  bounded context.
"""
