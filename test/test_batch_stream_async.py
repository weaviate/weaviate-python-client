"""Unit tests for the async batch-stream failure handling (no cluster needed)."""

import asyncio
import logging
from typing import Optional

import pytest

from weaviate.collections.batch.async_ import _BatchBaseAsync, _BgTasks
from weaviate.collections.batch.base import _BatchDataWrapper
from weaviate.collections.batch.batch_wrapper import _ContextManagerAsync
from weaviate.exceptions import WeaviateBatchStreamError


class _NotAnException(BaseException):
    """Escapes the wrappers' `except Exception` like grpc.aio's CancelledError does."""


def _bare_batch(**mangled) -> _BatchBaseAsync:
    batch = object.__new__(_BatchBaseAsync)
    for name, value in mangled.items():
        setattr(batch, f"_BatchBaseAsync__{name}", value)
    return batch


class _FakeTimeouts:
    insert = 1


class _FakeConnection:
    timeout_config = _FakeTimeouts()


def test_wait_raises_the_background_exception_and_keeps_partial_results() -> None:
    # a background failure must not come back as a success, and a user catching it
    # must still see what failed
    class FakeBgTasks:
        async def gather(self, timeout=None) -> None:
            return None

    partial = _BatchDataWrapper()
    partial.failed_objects = ["sentinel-failure"]  # type: ignore[list-item]
    backup = _BatchDataWrapper()
    batch = _bare_batch(
        bg_exception=RuntimeError("boom"),
        bg_tasks=FakeBgTasks(),
        connection=_FakeConnection(),
        results_for_wrapper=partial,
        results_for_wrapper_backup=backup,
    )

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(batch._wait())
    assert backup.failed_objects == ["sentinel-failure"]


def test_flush_raises_when_a_task_dies_without_setting_bg_exception() -> None:
    # loop_wrapper/recv_wrapper only catch Exception, so a BaseException kills a task with
    # __bg_exception unset; flush() must notice the dead task instead of spinning forever
    async def run() -> None:
        async def dies() -> None:
            raise _NotAnException("boom")

        loop_task = asyncio.get_running_loop().create_task(asyncio.sleep(3600))
        recv_task = asyncio.get_running_loop().create_task(dies())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert recv_task.done()

        batch = _bare_batch(
            bg_exception=None,
            bg_tasks=_BgTasks(recv=recv_task, loop=loop_task),
            batch_objects=[object()],
            batch_references=[],
        )
        try:
            await asyncio.wait_for(batch.flush(), timeout=2)  # a regression hangs here
        finally:
            loop_task.cancel()

    with pytest.raises(WeaviateBatchStreamError, match="stream has ended"):
        asyncio.run(run())


class _FakeBatch:
    """Stands in for _BatchBaseAsync behind the context manager."""

    def __init__(self, wait_error: Optional[BaseException] = None) -> None:
        self.wait_error = wait_error
        self.wait_called = False

    async def _start(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def _wait(self) -> None:
        self.wait_called = True
        if self.wait_error is not None:
            raise self.wait_error


def test_aexit_raises_a_background_failure_on_a_clean_block() -> None:
    fake = _FakeBatch(WeaviateBatchStreamError("bg died"))

    async def run() -> None:
        async with _ContextManagerAsync(fake):  # type: ignore[arg-type]
            pass

    with pytest.raises(WeaviateBatchStreamError, match="bg died"):
        asyncio.run(run())


def test_aexit_keeps_the_users_exception_over_a_background_failure(caplog) -> None:
    # the block's own exception must not be replaced by the background failure
    fake = _FakeBatch(WeaviateBatchStreamError("bg died"))

    async def run() -> None:
        async with _ContextManagerAsync(fake):  # type: ignore[arg-type]
            raise ValueError("user code")

    with caplog.at_level(logging.WARNING, logger="weaviate-client"):
        with pytest.raises(ValueError, match="user code"):
            asyncio.run(run())
    assert fake.wait_called  # still drained/awaited
    assert "bg died" in caplog.text
