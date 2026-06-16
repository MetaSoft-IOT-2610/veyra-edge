"""Peewee ORM model for the Monitoring bounded context.

Defines the ``measurements`` table used to buffer
:class:`~monitoring.domain.entities.Measurement` domain entities locally before
they are synchronized to the cloud.  This module belongs to the infrastructure
layer and must not be referenced directly from the domain or application
layers; access is mediated through the repository.
"""
from peewee import (
    Model, AutoField, CharField, IntegerField, FloatField, DateTimeField, BooleanField
)

from shared.infrastructure.database import db


class Measurement(Model):
    """ORM mapping for the ``measurements`` table.

    Each row represents a single vital-signs reading buffered at the edge.  The
    ``synced`` flag supports the offline-buffer / cloud-sync workflow: readings
    are stored with ``synced = False`` and flipped to ``True`` once successfully
    published to the cloud backend.

    Attributes:
        id (AutoField): Auto-incrementing integer primary key.
        device_id (CharField): Stable backend identifier of the device.
        mac_address (CharField): Hardware MAC address of the device.
        nursing_home_id (IntegerField): Owning nursing-home identifier.
        timestamp (DateTimeField): UTC timestamp of the reading.
        heart_rate (IntegerField): Heart rate in bpm (nullable).
        systolic (IntegerField): Systolic blood pressure in mmHg (nullable).
        diastolic (IntegerField): Diastolic blood pressure in mmHg (nullable).
        temperature (FloatField): Temperature in Celsius (nullable).
        oxygen_saturation (IntegerField): Oxygen saturation percentage (nullable).
        respiratory_rate (IntegerField): Respiratory rate in breaths/min (nullable).
        synced (BooleanField): Whether the reading was published to the cloud.
        created_at (DateTimeField): UTC timestamp of when the row was buffered.
    """

    id = AutoField()
    device_id = CharField()
    mac_address = CharField()
    nursing_home_id = IntegerField()
    timestamp = DateTimeField()
    heart_rate = IntegerField(null=True)
    systolic = IntegerField(null=True)
    diastolic = IntegerField(null=True)
    temperature = FloatField(null=True)
    oxygen_saturation = IntegerField(null=True)
    respiratory_rate = IntegerField(null=True)
    synced = BooleanField(default=False)
    created_at = DateTimeField()

    class Meta:
        """Peewee metadata: binds the model to the shared database and names the table."""

        database = db
        table_name = 'measurements'
