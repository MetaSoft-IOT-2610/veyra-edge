"""Peewee ORM model for the IAM bounded context.

Defines the ``devices`` table used to persist
:class:`~iam.domain.entities.Device` aggregate roots provisioned by the cloud
backend.  This module belongs to the infrastructure layer; it must not be
imported directly by the domain or application layers — access is mediated
through the repository.
"""
from peewee import Model, AutoField, CharField, IntegerField, DateTimeField

from shared.infrastructure.database import db


class Device(Model):
    """ORM mapping for the ``devices`` table.

    Each row represents an IoT device provisioned at the edge by the backend,
    together with the credentials and tenant information required to
    authenticate and route its telemetry.

    Attributes:
        id (AutoField): Auto-incrementing surrogate primary key.
        device_id (CharField): Stable identifier assigned by the backend.
            Unique within the edge registry.
        mac_address (CharField): Hardware MAC address used by the device to
            identify itself when sending telemetry.  Unique and mutable.
        nursing_home_id (IntegerField): Identifier of the owning nursing home.
        device_type (CharField): Device category (``'VITAL_SIGNS'`` or
            ``'GPS'``).
        api_key (CharField): Secret key checked on every telemetry request.
        created_at (DateTimeField): UTC timestamp of device registration.
        updated_at (DateTimeField): UTC timestamp of the last update.
    """

    id = AutoField()
    device_id = CharField(unique=True)
    mac_address = CharField(unique=True)
    nursing_home_id = IntegerField()
    device_type = CharField()
    api_key = CharField()
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        """Peewee metadata: binds the model to the shared database and names the table."""

        database = db
        table_name = 'devices'
