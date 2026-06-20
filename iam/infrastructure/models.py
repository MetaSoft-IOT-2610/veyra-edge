"""Peewee ORM model for the IAM bounded context."""
from peewee import Model, AutoField, CharField, DateTimeField

from shared.infrastructure.database import db


class Device(Model):
    """ORM mapping for the ``devices`` table — local mirror of the cloud registry."""

    id = AutoField()
    device_id = CharField(unique=True)
    device_type = CharField()
    mac_address = CharField(unique=True)
    status = CharField(default="ACTIVE")
    cloud_updated_at = DateTimeField(null=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        database = db
        table_name = 'devices'
