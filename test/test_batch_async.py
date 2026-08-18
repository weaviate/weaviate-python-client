"""Unit tests for the async batch-stream failure handling.

These pin the behaviors added for WASM/background-failure robustness without needing a
cluster: the grpc-web fail-fast in _start, flush() raising instead of spinning forever
(whether or not __bg_exception was set), and _wait() preserving partial results while
still raising.
"""

import asyncio
import logging
from typing import Optional

import grpc
import pytest

from weaviate.collections.batch.async_ import _BatchBaseAsync, _BgTasks
from weaviate.collections.batch.base import _BatchDataWrapper
from weaviate.collections.batch.batch_wrapper import _ContextManagerAsync
from weaviate.exceptions import WeaviateBatchStreamError, _BatchStreamShutdownError


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


async def _finished_task() -> "asyncio.Task[None]":
    """A background task that returned normally (e.g. the server closed the stream)."""
    task = asyncio.get_running_loop().create_task(asyncio.sleep(0))
    await task
    return task


class _FakeTimeouts:
    insert = 1


class _FakeConnection:
    timeout_config = _FakeTimeouts()


def test_wait_names_unsent_data_when_the_tasks_ended_cleanly() -> None:
    # both tasks returned normally (server closed the stream) with data still queued:
    # that is not "the background tasks died unexpectedly", it is an early end of the
    # stream — say what was left behind
    async def run() -> None:
        batch = _bare_batch(
            bg_exception=None,
            bg_tasks=_BgTasks(recv=await _finished_task(), loop=await _finished_task()),
            connection=_FakeConnection(),
            results_for_wrapper=_BatchDataWrapper(),
            results_for_wrapper_backup=_BatchDataWrapper(),
            batch_objects=[object(), object()],
            batch_references=[object()],
        )
        await batch._wait()

    with pytest.raises(
        WeaviateBatchStreamError, match="ended with 2 objects and 1 references unsent"
    ):
        asyncio.run(run())


def test_check_alive_after_a_clean_end_says_the_stream_ended() -> None:
    async def run() -> None:
        batch = _bare_batch(
            bg_exception=None,
            bg_tasks=_BgTasks(recv=await _finished_task(), loop=await _finished_task()),
        )
        getattr(batch, "_BatchBaseAsync__check_bg_tasks_alive")()  # noqa: B009

    with pytest.raises(WeaviateBatchStreamError, match="stream has ended"):
        asyncio.run(run())


def test_put_gives_up_when_the_tasks_are_dead() -> None:
    # a full queue with a dead receiver never drains: __put must return False instead of
    # retrying (and recursing) once per second forever
    async def run() -> bool:
        reqs: asyncio.Queue = asyncio.Queue(maxsize=1)
        await reqs.put(object())  # full
        batch = _bare_batch(
            reqs=reqs,
            bg_exception=None,  # nothing recorded ...
            shutdown_loop=asyncio.Event(),  # ... and no shutdown either
            bg_tasks=_BgTasks(recv=await _dead_task("cancel"), loop=await _finished_task()),
        )
        put = getattr(batch, "_BatchBaseAsync__put")  # noqa: B009
        return await asyncio.wait_for(put(object()), timeout=5)

    assert asyncio.run(run()) is False


def test_batch_stream_shutdown_error_is_in_the_taxonomy() -> None:
    # raised on gRPC ABORTED and can surface from a clean `async with` exit
    assert issubclass(_BatchStreamShutdownError, WeaviateBatchStreamError)
    assert isinstance(_BatchStreamShutdownError(), Exception)


class _FakeBatch:
    """Stands in for _BatchBaseAsync behind the context manager."""

    def __init__(self, wait_error: Optional[BaseException] = None) -> None:
        self.wait_error = wait_error
        self.shutdown_called = False
        self.wait_called = False

    async def _start(self) -> None:
        pass

    async def _shutdown(self) -> None:
        self.shutdown_called = True

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
    # the block's own exception must not be REPLACED by the background failure (which
    # used to demote it to __context__); the failure is logged instead
    fake = _FakeBatch(WeaviateBatchStreamError("bg died"))

    async def run() -> None:
        async with _ContextManagerAsync(fake):  # type: ignore[arg-type]
            raise ValueError("user code")

    with caplog.at_level(logging.WARNING, logger="weaviate-client"):
        with pytest.raises(ValueError, match="user code"):
            asyncio.run(run())
    assert fake.shutdown_called and fake.wait_called  # still drained/awaited
    assert "bg died" in caplog.text


def test_aexit_never_swallows_cancellation() -> None:
    # a CancelledError leaving the block used to be replaced by the background failure,
    # i.e. the cancellation was swallowed
    fake = _FakeBatch(WeaviateBatchStreamError("bg died"))

    async def run() -> None:
        async with _ContextManagerAsync(fake):  # type: ignore[arg-type]
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run())
    assert fake.wait_called


def test_wait_with_an_infinite_insert_timeout_does_not_raise() -> None:
    # Timeout(insert=inf) means "no deadline": the shutdown wait must not turn it into an
    # error (the sync colour's Thread.join(inf) overflows; keep both colours consistent)
    from weaviate.config import Timeout as TimeoutConfig

    class InfiniteInsert:
        timeout_config = TimeoutConfig(insert=float("inf"))

    async def run() -> None:
        batch = _bare_batch(
            bg_exception=None,
            bg_tasks=_BgTasks(recv=await _finished_task(), loop=await _finished_task()),
            connection=InfiniteInsert(),
            results_for_wrapper=_BatchDataWrapper(),
            results_for_wrapper_backup=_BatchDataWrapper(),
            batch_objects=[],
            batch_references=[],
        )
        await batch._wait()

    asyncio.run(run())


def test_aexit_does_not_log_the_exception_that_is_already_propagating(caplog) -> None:
    # flush()/add_object raised __bg_exception inside the block; _wait() re-raises the
    # SAME object on exit — that is not a second failure to log
    err = WeaviateBatchStreamError("bg died")
    fake = _FakeBatch(err)

    async def run() -> None:
        async with _ContextManagerAsync(fake):  # type: ignore[arg-type]
            raise err

    with caplog.at_level(logging.WARNING, logger="weaviate-client"):
        with pytest.raises(WeaviateBatchStreamError, match="bg died"):
            asyncio.run(run())
    assert fake.wait_called
    assert "batch stream failed" not in caplog.text
