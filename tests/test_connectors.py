import threading
import time
from qbackup.connectors import LocalDataConnector


def test_local_connector_load_default_when_file_does_exists(tmpdir):
    expected_first = "foo bar"
    expected_second = ["foo", "bar"]
    with LocalDataConnector(tmpdir, expected_first) as connector:
        assert connector.load() == expected_first
        connector.dump(expected_second)
        assert connector.load() == expected_second


def test_local_connector_is_only_added_on_lock_release(tmpdir):
    def func():
        with LocalDataConnector(tmpdir, {}) as conn_thread:
            conn_thread.dump({})
            time.sleep(2)

    threading.Thread(target=func, args=()).start()

    time.sleep(1)

    with LocalDataConnector(tmpdir, {}) as connector:
        expected = dict(
            foo='bar',
            baz=123,
        )

        connector.dump(expected)
        result = connector.load()

        assert result == expected