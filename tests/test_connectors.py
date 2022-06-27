import sqlite3
import threading
import time
from unittest.mock import Mock

import pytest
from qbackup.connectors import FileBackedConnector, SqliteConnector


def test_file_backed_connectors_are_mutually_exclusive_succeed(tmpdir):
    def func():
        with FileBackedConnector(tmpdir):
            time.sleep(2)

    threading.Thread(target=func, args=()).start()

    # wait `func()` to finish
    time.sleep(3)

    with FileBackedConnector(tmpdir):
        pass


def test_file_backed_connectors_are_mutually_exclusive_fail(tmpdir):
    def func():
        with FileBackedConnector(tmpdir):
            time.sleep(2)

    threading.Thread(target=func, args=()).start()
    
    with pytest.raises(OSError):
        with FileBackedConnector(tmpdir):
            pass


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
