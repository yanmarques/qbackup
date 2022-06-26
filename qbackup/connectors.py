"""
Configuration utility functions
"""

import fcntl
import os
import sqlite3
from pathlib import Path
from typing import Optional, cast

from .api import AbstractDataConnector


class FileBackedConnector(AbstractDataConnector):

    lock_name = "qbackup.lock"

    def __init__(self, path) -> None:
        super().__init__()
        self._lock_file: Path = Path(path) / self.lock_name
        self._lock_file_fd: Optional[int] = None

    def connect(self) -> None:
        open_mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        fd = os.open(self._lock_file, open_mode)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
        else:
            self._lock_file_fd = fd

    def close(self) -> None:
        # Do not remove the lockfile:
        #   https://github.com/tox-dev/py-filelock/issues/31
        #   https://stackoverflow.com/questions/17708885/flock-removing-locked-file-without-race-condition
        if self._lock_file_fd:
            fd = cast(int, self._lock_file_fd)
            self._lock_file_fd = None
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


class SqliteConnector(AbstractDataConnector):
    def __init__(self, database: str, bootstrap_sql: str = None) -> None:
        super().__init__()
        self._database = database
        self._bootstrap_sql = bootstrap_sql
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self._database)
        if self._bootstrap_sql is not None:
            self._conn.executescript(self._bootstrap_sql)
            self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
