"""Peewee ORM model for the IAM bounded context.

Defines the ``devices`` table used to persist
:class:`~iam.domain.entities.Device` aggregate roots provisioned by the cloud
backend.  This module belongs to the infrastructure layer; it must not be
imported directly by the domain or application layers — access is mediated
through the repository.
"""
from peewee import Model, AutoField, CharField, DateTimeField

from shared.infrastructure.database import db


class Device(Model):
    """ORM mapping for the ``devices`` table.

    Each row represents an IoT node registered at the edge with a stable
    ``device_id`` and an ``api_key`` used to authenticate telemetry.

    Attributes:
        id (AutoField): Auto-incrementing surrogate primary key.
        device_id (CharField): Stable node identifier.  Unique within the edge
            registry.
        device_type (CharField): Device category (``'VITAL_SIGNS'`` or
            ``'GPS'``).
        api_key (CharField): Secret key checked on every telemetry request.
        created_at (DateTimeField): UTC timestamp of device registration.
        updated_at (DateTimeField): UTC timestamp of the last update.
    """

    id = AutoField()
    device_id = CharField(unique=True)
    device_type = CharField()
    api_key = CharField()
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        """Peewee metadata: binds the model to the shared database and names the table."""

        database = db
        table_name = 'devices'
