import faulthandler
import os
import threading

import pytest

DEFAULT_TIMEOUT = 300  # 5 minutes

_timeout_timer: threading.Timer | None = None


def _get_timeout(item: pytest.Item) -> float:
    marker = item.get_closest_marker("timeout")
    if marker and marker.args:
        return float(marker.args[0])
    return float(DEFAULT_TIMEOUT)


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Start a watchdog timer that dumps all thread stack traces on timeout.

    Unlike pytest-timeout, this does NOT raise KeyboardInterrupt (which crashes
    xdist workers and corrupts asyncio event loops). Instead it:
    1. Writes the test name + all thread tracebacks directly to fd 2 (stderr).
       With --capture=sys in pytest.ini, fd 2 is the real stderr (not captured),
       so the output goes directly to the CI log even under xdist.
    2. Calls os._exit(1) to terminate the worker process.

    xdist will report 'node down: Not properly terminated' which is expected —
    the diagnostic output will already be in the CI logs above that message.
    """
    global _timeout_timer
    timeout = _get_timeout(item)
    if timeout <= 0:
        return

    def _on_timeout() -> None:
        banner = "=" * 70
        os.write(2, f"\n\n{banner}\n".encode())
        os.write(2, f"TIMEOUT: {item.nodeid} exceeded {timeout}s\n".encode())
        os.write(2, f"{banner}\n\n".encode())
        # faulthandler needs a file object — wrap a dup of fd 2 to avoid closing it
        with os.fdopen(os.dup(2), "w") as f:
            faulthandler.dump_traceback(file=f)
            f.flush()
        os.write(2, f"\n{banner}\n\n".encode())
        os._exit(1)

    _timeout_timer = threading.Timer(timeout, _on_timeout)
    _timeout_timer.daemon = True
    _timeout_timer.start()


def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    """Cancel the watchdog timer after each test completes."""
    global _timeout_timer
    if _timeout_timer is not None:
        _timeout_timer.cancel()
        _timeout_timer = None
