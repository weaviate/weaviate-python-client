import faulthandler

import pytest


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Set faulthandler alarm as a backup timeout mechanism.

    This fires even if the process is stuck in C code (e.g., gRPC core).
    Set to pytest-timeout value + 30s so pytest-timeout handles it first.

    Uses exit=False to avoid killing xdist worker processes — a killed worker
    causes 'node down: Not properly terminated' and loses the stack trace output.
    With exit=False, faulthandler dumps tracebacks to stderr (relayed by xdist)
    without terminating the process, letting pytest-timeout handle the interruption.
    """
    marker = item.get_closest_marker("timeout")
    if marker and marker.args:
        test_timeout = marker.args[0]
    else:
        test_timeout = item.config.getini("timeout") or 300

    if test_timeout and float(test_timeout) > 0:
        faulthandler.dump_traceback_later(float(test_timeout) + 30, exit=False)


def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    """Cancel the faulthandler alarm after each test."""
    faulthandler.cancel_dump_traceback_later()
