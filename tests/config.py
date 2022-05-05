from pathlib import Path
import threading
import time
import qbackup.config


def test_config_is_only_added_on_lock_release(tmpdir):
    def func():
        with qbackup.config.Config(tmpdir) as config_thread:
            config_thread.dump({})
            time.sleep(2)

    threading.Thread(target=func, args=()).start()

    time.sleep(1)

    with qbackup.config.Config(tmpdir) as config:
        expected = dict(
            foo='bar',
            baz=123,
        )

        config.dump(expected)

        result = config.load()

        assert result == expected