"""Unit tests for the sync batch-stream failure handling (no cluster needed)."""

import logging
import time
from typing import Optional

import pytest

from weaviate.collections.batch.base import _BatchDataWrapper
from weaviate.collections.batch.batch_wrapper import _ContextManagerSync
from weaviate.collections.batch.sync import _BatchBaseSync
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


def test_wait_raises_the_background_exception_and_keeps_partial_results() -> None:
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


def test_start_raises_the_stored_background_exception_at_once() -> None:
    # a background thread that died right away (e.g. on a closed connection) used to leave
    # _start polling for 60 s and then blaming the network (#2139)
    batch = _bare_batch(bg_exception=None, bg_threads=None)

    def start_dead_threads() -> None:
        setattr(batch, "_BatchBaseSync__bg_threads", _FakeThreads(alive=False))
        setattr(batch, "_BatchBaseSync__bg_exception", RuntimeError("connection closed"))

    setattr(batch, "_BatchBaseSync__start_bg_threads", start_dead_threads)
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="connection closed"):
        batch._start()
    assert time.monotonic() - started < 5


class _FakeBatch:
    def __init__(self, wait_error: Optional[BaseException] = None) -> None:
        self.wait_error = wait_error
        self.wait_called = False

    def _start(self) -> None:
        pass

    def _shutdown(self) -> None:
        pass

    def _wait(self) -> None:
        self.wait_called = True
        if self.wait_error is not None:
            raise self.wait_error


def test_exit_raises_a_background_failure_on_a_clean_block() -> None:
    # the sync colour used to swallow this entirely
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
    assert fake.wait_called
    assert "bg died" in caplog.text
