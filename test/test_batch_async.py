"""Unit tests for the async batch-stream failure handling.

These pin the behaviors added for WASM/background-failure robustness without needing a
cluster: the grpc-web fail-fast in _start, flush() raising instead of spinning forever
(whether or not __bg_exception was set), and _wait() preserving partial results while
still raising.
"""

import asyncio

import grpc
import pytest

from weaviate.collections.batch.async_ import _BatchBaseAsync, _BgTasks
from weaviate.collections.batch.base import _BatchDataWrapper
from weaviate.exceptions import WeaviateBatchStreamError


class _NotAnException(BaseException):
    """Stands in for what grpc.aio can raise past `except Exception` in the wrappers.

    A custom BaseException, not KeyboardInterrupt/SystemExit: asyncio re-raises those two
    out of Task.__step and would tear down the test's event loop.
    """


def _bare_batch(**mangled) -> _BatchBaseAsync:
    batch = object.__new__(_BatchBaseAsync)
    for name, value in mangled.items():
        setattr(batch, f"_BatchBaseAsync__{name}", value)
    return batch


async def _dead_task(mode: str) -> "asyncio.Task[None]":
    """A background task that is already done with __bg_exception left unset."""

    async def forever() -> None:
        await asyncio.sleep(3600)

    async def dies() -> None:
        raise _NotAnException("boom")

    task = asyncio.get_running_loop().create_task(forever() if mode == "cancel" else dies())
    if mode == "cancel":
        task.cancel()
    await asyncio.sleep(0)
    await asyncio.sleep(0)  # let the task reach its end state
    assert task.done()
    return task


def test_start_fails_fast_when_grpc_web_shim_active(monkeypatch) -> None:
    # over grpc-web the BatchStream RPC would die inside the background tasks (silent
    # drop / endless flush); _start must raise before any task is created
    monkeypatch.setattr(grpc, "__weaviate_client_web_shim__", True, raising=False)
    batch = _bare_batch()  # the guard runs before any attribute access
    with pytest.raises(WeaviateBatchStreamError, match="insert_many"):
        asyncio.run(batch._start())


def test_flush_raises_background_exception_instead_of_hanging() -> None:
    # with dead background tasks nothing drains the queues; flush used to spin on
    # asyncio.sleep(0.01) forever
    batch = _bare_batch(
        bg_exception=RuntimeError("boom"),
        bg_tasks=None,
        batch_objects=[object()],
        batch_references=[],
    )

    async def flush_with_deadline() -> None:
        await asyncio.wait_for(batch.flush(), timeout=2)

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(flush_with_deadline())


@pytest.mark.parametrize("mode", ["cancel", "base_exception"])
def test_flush_raises_when_a_task_dies_without_setting_bg_exception(mode: str) -> None:
    # loop_wrapper/recv_wrapper only catch Exception, so a BaseException — e.g. the
    # CancelledError grpc.aio raises on a cancelled streaming call — kills a task with
    # __bg_exception unset. flush() must notice the dead task, like its sync twin's
    # __check_bg_threads_alive(), instead of spinning forever.
    async def run() -> None:
        loop_task = asyncio.get_running_loop().create_task(asyncio.sleep(3600))
        recv_task = await _dead_task(mode)

        batch = _bare_batch(
            bg_exception=None,  # nothing recorded: that is the whole point
            bg_tasks=_BgTasks(recv=recv_task, loop=loop_task),
            batch_objects=[object()],
            batch_references=[],
        )
        try:
            # the deadline makes a regression fail fast instead of hanging CI
            await asyncio.wait_for(batch.flush(), timeout=2)
        finally:
            loop_task.cancel()

    with pytest.raises(WeaviateBatchStreamError, match="background receive task"):
        asyncio.run(run())


def test_wait_raises_when_tasks_die_with_data_still_queued() -> None:
    # _wait() returning quietly here would report a partial import as a success
    class FakeTimeouts:
        insert = 1

    class FakeConnection:
        timeout_config = FakeTimeouts()

    async def run() -> None:
        recv_task = await _dead_task("base_exception")
        loop_task = await _dead_task("base_exception")

        batch = _bare_batch(
            bg_exception=None,
            bg_tasks=_BgTasks(recv=recv_task, loop=loop_task),
            connection=FakeConnection(),
            results_for_wrapper=_BatchDataWrapper(),
            results_for_wrapper_backup=_BatchDataWrapper(),
            batch_objects=[object()],  # still queued => the batch did not complete
            batch_references=[],
        )
        await batch._wait()

    with pytest.raises(WeaviateBatchStreamError, match="background receive task"):
        asyncio.run(run())


def test_wait_copies_partial_results_before_raising() -> None:
    # a user catching the background failure must still see what failed
    class FakeBgTasks:
        async def gather(self, timeout=None) -> None:
            return None

    class FakeTimeouts:
        insert = 1

    class FakeConnection:
        timeout_config = FakeTimeouts()

    partial = _BatchDataWrapper()
    partial.failed_objects = ["sentinel-failure"]  # type: ignore[list-item]
    backup = _BatchDataWrapper()

    batch = _bare_batch(
        bg_exception=RuntimeError("boom"),
        bg_tasks=FakeBgTasks(),
        connection=FakeConnection(),
        results_for_wrapper=partial,
        results_for_wrapper_backup=backup,
    )

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(batch._wait())
    assert backup.failed_objects == ["sentinel-failure"]
