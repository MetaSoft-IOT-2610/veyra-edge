"""Peewee ORM model for the Monitoring bounded context.

Defines the ``measurements`` table used to buffer
:class:`~monitoring.domain.entities.Measurement` domain entities locally before
they are synchronized to the cloud.  This module belongs to the infrastructure
layer and must not be referenced directly from the domain or application
layers; access is mediated through the repository.
"""
from peewee import (
    Model, AutoField, CharField, IntegerField, FloatField, DateTimeField, BooleanField, TextField
)

from shared.infrastructure.database import db


class Threshold(Model):
    """ORM mapping for the ``thresholds`` table.

    Each row holds the vital-sign alert bounds the cloud has configured for one
    device.  Rows are created or updated by the threshold sync gateway; the edge
    never writes to this table itself.

    Attributes:
        id (AutoField): Auto-incrementing integer primary key.
        device_id (CharField): Stable node identifier (unique per device).
        heart_rate_min/max (IntegerField): Heart rate bounds in bpm (nullable).
        systolic_min/max (IntegerField): Systolic pressure bounds in mmHg (nullable).
        diastolic_min/max (IntegerField): Diastolic pressure bounds in mmHg (nullable).
        temperature_min/max (FloatField): Temperature bounds in °C (nullable).
        oxygen_saturation_min/max (IntegerField): SpO₂ bounds in % (nullable).
        respiratory_rate_min/max (IntegerField): Respiratory rate bounds (nullable).
        cloud_updated_at (DateTimeField): UTC timestamp of the last cloud update.
        updated_at (DateTimeField): UTC timestamp of the last local upsert.
    """

    id = AutoField()
    device_id = CharField(unique=True)
    heart_rate_min = IntegerField(null=True)
    heart_rate_max = IntegerField(null=True)
    systolic_min = IntegerField(null=True)
    systolic_max = IntegerField(null=True)
    diastolic_min = IntegerField(null=True)
    diastolic_max = IntegerField(null=True)
    temperature_min = FloatField(null=True)
    temperature_max = FloatField(null=True)
    oxygen_saturation_min = IntegerField(null=True)
    oxygen_saturation_max = IntegerField(null=True)
    respiratory_rate_min = IntegerField(null=True)
    respiratory_rate_max = IntegerField(null=True)
    cloud_updated_at = DateTimeField(null=True)
    updated_at = DateTimeField()

    class Meta:
        database = db
        table_name = 'thresholds'


class Measurement(Model):
    """ORM mapping for the ``measurements`` table.

    Each row represents a single vital-signs reading buffered at the edge.  The
    ``synced`` flag supports the offline-buffer / cloud-sync workflow: readings
    are stored with ``synced = False`` and flipped to ``True`` once successfully
    published to the cloud backend.

    Attributes:
        id (AutoField): Auto-incrementing integer primary key.
        device_id (CharField): Stable node identifier of the device.
        device_type (CharField): Device category from the gateway registry.
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
    device_id = CharField(index=True)
    device_type = CharField()
    timestamp = DateTimeField(index=True)
    heart_rate = IntegerField(null=True)
    systolic = IntegerField(null=True)
    diastolic = IntegerField(null=True)
    temperature = FloatField(null=True)
    oxygen_saturation = IntegerField(null=True)
    respiratory_rate = IntegerField(null=True)
    ambient_temperature = FloatField(null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    satellite_count = IntegerField(null=True)
    satellites_in_view = IntegerField(null=True)
    diagnostics_json = TextField(null=True)
    synced = BooleanField(default=False, index=True)
    created_at = DateTimeField()

    class Meta:
        """Peewee metadata: binds the model to the shared database and names the table."""

        database = db
        table_name = 'measurements'
        indexes = (
            (("synced", "id"), False),
            (("device_id", "timestamp"), False),
        )
