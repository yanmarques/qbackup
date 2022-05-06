"""
Configuration utility functions
"""

import os
from pathlib import Path
import yaml
import fcntl
from typing import Dict, cast
from .api import AbstractDataConnector


class LocalDataConnector(AbstractDataConnector):

    config_name = 'config.yaml'
    lock_name = 'qbackup.lock'

    def __init__(self, path: str, default) -> None:
        super().__init__()
        self._default = default
        self._path: Path = Path(path)
        self._lock_file: Path = path / self.lock_name
        self._config_file: Path = path / self.config_name
        self._lock_file_fd: int = None

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

    def load(self) -> Dict:
        if not self._config_file.exists():
            return self._default

        with open(self._config_file) as fp:
            return yaml.safe_load(fp)

    def dump(self, data) -> None:
        with open(self._config_file, 'w') as fp:
            yaml.safe_dump(data, fp)
