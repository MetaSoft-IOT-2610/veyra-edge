"""Shared database infrastructure for the Veyra Edge Service.

Provides a single :class:`peewee.SqliteDatabase` instance (``db``) imported by
the ORM models of every bounded context, ensuring all models operate on the
same physical SQLite file used for offline buffering at the edge.

The :func:`init_db` helper is called once at application start-up to open a
connection and create any missing tables without affecting existing data
(``safe=True``).
"""
from peewee import SqliteDatabase

from shared.infrastructure.config import EdgeConfig

# Shared SQLite database instance used by all bounded-context ORM models.
db = SqliteDatabase(EdgeConfig.SQLITE_DB_PATH)


def init_db() -> None:
    """Open the database connection and create all required tables.

    Imports the ORM models from the IAM and Monitoring bounded contexts at call
    time (deferred import) to avoid circular dependencies during module
    loading, then issues a ``CREATE TABLE IF NOT EXISTS`` for each model.

    This function is idempotent: calling it when the tables already exist is
    safe and has no side-effects (``safe=True`` suppresses ``CREATE TABLE``
    errors for pre-existing tables).

    Side effects:
        - Opens a connection to the configured SQLite file (creating it if it
          does not exist).
        - Creates the ``devices`` table if absent.
        - Creates the ``measurements`` table if absent.
        - Creates the ``thresholds`` table if absent.
        - Closes the connection after table creation.
    """
    db.connect()
    from iam.infrastructure.models import Device
    from monitoring.infrastructure.models import Measurement, Threshold
    db.create_tables([Device, Measurement, Threshold], safe=True)
    db.close()
