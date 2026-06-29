"""Shared pytest fixtures for the Veyra Edge test suite."""
import pytest
import peewee

from monitoring.infrastructure.models import Threshold as ThresholdModel

TEST_DB = peewee.SqliteDatabase(":memory:")


@pytest.fixture
def db():
    """Bind ThresholdModel to an in-memory SQLite database for the duration of the test."""
    with TEST_DB.bind_ctx([ThresholdModel]):
        TEST_DB.connect()
        TEST_DB.create_tables([ThresholdModel])
        yield TEST_DB
        TEST_DB.drop_tables([ThresholdModel])
        TEST_DB.close()
