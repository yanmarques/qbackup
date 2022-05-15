import sqlite3
import threading
import time
from unittest.mock import Mock
from qbackup.connectors import FileBackedConnector, SqliteConnector


def test_file_backed_connectors_are_mutually_exclusive(tmpdir):
    shared_data = {}

    def func():
        with FileBackedConnector(tmpdir):
            shared_data["step"] = "first"
            time.sleep(2)

        with FileBackedConnector(tmpdir):
            assert shared_data.get("step") == "second"

    threading.Thread(target=func, args=()).start()

    time.sleep(1)

    with FileBackedConnector(tmpdir):
        assert shared_data.get("step") == "first"
        shared_data["step"] = "second"


def test_sqlite_connector_creates_and_closes_connection(monkeypatch):
    mock_connection = Mock()
    mock_connect = Mock(return_value=mock_connection)

    monkeypatch.setattr(sqlite3, "connect", mock_connect)

    with SqliteConnector("db"):
        pass

    mock_connect.assert_called_once_with("db")
    mock_connection.close.assert_called_once()


def test_sqlite_connector_automatically_execute_bootstrap_sql(monkeypatch):
    sql = """CREATE TABLE test (id VARCHAR PRIMARY KEY);"""

    mock_connection = Mock()
    mock_connect = Mock(return_value=mock_connection)

    monkeypatch.setattr(sqlite3, "connect", mock_connect)

    with SqliteConnector("db", sql):
        mock_connection.executescript.assert_called_once_with(sql)
        mock_connection.commit.assert_called_once()
