import faulthandler

import pytest


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Set faulthandler alarm as a backup timeout mechanism.

    This fires even if the process is stuck in C code (e.g., gRPC core).
    Set to pytest-timeout value + 30s so pytest-timeout handles it first.
    """
    marker = item.get_closest_marker("timeout")
    if marker and marker.args:
        test_timeout = marker.args[0]
    else:
        test_timeout = item.config.getini("timeout") or 300

    if test_timeout and float(test_timeout) > 0:
        faulthandler.dump_traceback_later(float(test_timeout) + 30, exit=True)


def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    """Cancel the faulthandler alarm after each test."""
    faulthandler.cancel_dump_traceback_later()
