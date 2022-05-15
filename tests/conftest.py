from typing import Any
from pytest import fixture
from qbackup.api import AbstractDataConnector, AbstractReadWriteStream
from qbackup.database import StreamDataManager


class DummyDataConnector(AbstractDataConnector):
    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass


class DummyReadWriteStream(AbstractReadWriteStream):
    def load(self) -> Any:
        return self._default

    def dump(self, data) -> None:
        pass


@fixture
def dummy_connector():
    return DummyDataConnector()


@fixture
def dummy_rw_stream():
    return DummyReadWriteStream("/dev/null", {})
