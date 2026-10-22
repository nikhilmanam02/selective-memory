import pytest

from app.db import connect


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


@pytest.fixture
def connection(db_path):
    connection = connect()
    yield connection
    connection.close()
