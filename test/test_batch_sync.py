"""Unit tests for the sync batch-stream failure handling, mirroring test_batch_async.py.

_wait() surfaces a background failure (or data left unsent) instead of returning as if
the batch had succeeded, while an exception leaving the `with` block still wins.
"""

import logging
import threading
import time
from typing import Optional

import pytest

from weaviate.collections.batch.base import _BatchDataWrapper, _BgThreads
from weaviate.collections.batch.batch_wrapper import _ContextManagerSync
from weaviate.collections.batch.sync import _BatchBaseSync
from weaviate.config import Timeout as TimeoutConfig
from weaviate.exceptions import WeaviateBatchStreamError


def _bare_batch(**mangled) -> _BatchBaseSync:
    batch = object.__new__(_BatchBaseSync)
    for name, value in mangled.items():
        setattr(batch, f"_BatchBaseSync__{name}", value)
    return batch


class _FakeThreads:
    def __init__(self, alive: bool = False) -> None:
        self.alive = alive

    def join(self, timeout=None) -> None:
        return None

    def is_alive(self) -> bool:
        return self.alive


class _FakeTimeouts:
    insert = 1


class _FakeConnection:
    timeout_config = _FakeTimeouts()


def _batch_for_wait(**mangled) -> _BatchBaseSync:
    defaults = {
        "bg_exception": None,
        "bg_threads": _FakeThreads(alive=False),
        "connection": _FakeConnection(),
        "results_for_wrapper": _BatchDataWrapper(),
        "results_for_wrapper_backup": _BatchDataWrapper(),
        "batch_objects": [],
        "batch_references": [],
    }
    defaults.update(mangled)
    return _bare_batch(**defaults)


def test_wait_returns_quietly_when_everything_was_sent() -> None:
    _batch_for_wait()._wait()


def test_wait_raises_the_background_exception_and_keeps_partial_results() -> None:
    # like the async colour: a background failure must not come back as a success
    partial = _BatchDataWrapper()
    partial.failed_objects = ["sentinel-failure"]  # type: ignore[list-item]
    backup = _BatchDataWrapper()
    batch = _batch_for_wait(
        bg_exception=RuntimeError("boom"),
        results_for_wrapper=partial,
        results_for_wrapper_backup=backup,
    )

    with pytest.raises(RuntimeError, match="boom"):
        batch._wait()
    assert backup.failed_objects == ["sentinel-failure"]


def test_wait_names_unsent_data_when_the_threads_are_gone() -> None:
    batch = _batch_for_wait(batch_objects=[object(), object()], batch_references=[object()])
    with pytest.raises(
        WeaviateBatchStreamError, match="ended with 2 objects and 1 references unsent"
    ):
        batch._wait()


def test_check_alive_raises_inside_the_taxonomy() -> None:
    # used to be a bare Exception("Batch thread died unexpectedly")
    batch = _bare_batch(bg_exception=None, bg_threads=_FakeThreads(alive=False))
    with pytest.raises(WeaviateBatchStreamError, match="stream has ended"):
        getattr(batch, "_BatchBaseSync__check_bg_threads_alive")()  # noqa: B009


class _FakeBatch:
    def __init__(self, wait_error: Optional[BaseException] = None) -> None:
        self.wait_error = wait_error
        self.shutdown_called = False
        self.wait_called = False

    def _start(self) -> None:
        pass

    def _shutdown(self) -> None:
        self.shutdown_called = True

    def _wait(self) -> None:
        self.wait_called = True
        if self.wait_error is not None:
            raise self.wait_error


def test_exit_raises_a_background_failure_on_a_clean_block() -> None:
    fake = _FakeBatch(WeaviateBatchStreamError("bg died"))
    with pytest.raises(WeaviateBatchStreamError, match="bg died"):
        with _ContextManagerSync(fake):  # type: ignore[type-var]
            pass


def test_exit_keeps_the_users_exception_over_a_background_failure(caplog) -> None:
    fake = _FakeBatch(WeaviateBatchStreamError("bg died"))
    with caplog.at_level(logging.WARNING, logger="weaviate-client"):
        with pytest.raises(ValueError, match="user code"):
            with _ContextManagerSync(fake):  # type: ignore[type-var]
                raise ValueError("user code")
    assert fake.shutdown_called and fake.wait_called
    assert "bg died" in caplog.text


def test_exit_never_swallows_a_base_exception() -> None:
    fake = _FakeBatch(WeaviateBatchStreamError("bg died"))
    with pytest.raises(KeyboardInterrupt):
        with _ContextManagerSync(fake):  # type: ignore[type-var]
            raise KeyboardInterrupt()
    assert fake.wait_called


def test_wait_with_an_infinite_insert_timeout_does_not_overflow_join() -> None:
    # Timeout(insert=inf) is accepted (it means "no deadline"), but Thread.join(inf)
    # raises OverflowError — the shutdown wait must become "no timeout" instead
    class InfiniteInsert:
        timeout_config = TimeoutConfig(insert=float("inf"))

    threads = _BgThreads(
        loop=threading.Thread(target=lambda: None), recv=threading.Thread(target=lambda: None)
    )
    threads.start_recv()
    threads.start_loop()
    time.sleep(0.1)  # let both finish; is_alive()/join() are deliberately not called yet
    _batch_for_wait(bg_threads=threads, connection=InfiniteInsert())._wait()


def test_exit_does_not_log_the_exception_that_is_already_propagating(caplog) -> None:
    # flush()/add_object raised __bg_exception inside the block; _wait() re-raises the
    # SAME object on exit — that is not a second failure to log
    err = WeaviateBatchStreamError("bg died")
    fake = _FakeBatch(err)
    with caplog.at_level(logging.WARNING, logger="weaviate-client"):
        with pytest.raises(WeaviateBatchStreamError, match="bg died"):
            with _ContextManagerSync(fake):  # type: ignore[type-var]
                raise err
    assert fake.wait_called
    assert "batch stream failed" not in caplog.text
