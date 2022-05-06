import os
from pytest import fixture
from qbackup.connectors import LocalDataConnector


@fixture
def test_connector(tmpdir):
    connector = LocalDataConnector(tmpdir, {})
    yield connector
    if connector._config_file.exists():
        os.unlink(connector._config_file)
