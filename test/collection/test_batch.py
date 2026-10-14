import asyncio
import os
import signal
import sys
import threading
import time
import uuid
from types import SimpleNamespace
from typing import Awaitable, Callable, Iterator

import pytest

from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.collections.batch.base import (
    _BatchBase,
    _BatchDataWrapper,
    _RateLimitedBatching,
)
from weaviate.collections.batch.grpc_batch import _validate_props
from weaviate.collections.batch.sync import _BatchBaseSync
from weaviate.collections.classes.batch import (
    MAX_STORED_RESULTS,
    BatchObject,
    BatchObjectReturn,
    BatchReference,
    BatchReferenceReturn,
    ErrorObject,
    ErrorReference,
    Shard,
)
from weaviate.exceptions import WeaviateInsertInvalidPropertyError


def _error_object(index: int) -> ErrorObject:
    return ErrorObject(
        message="something went wrong",
        object_=BatchObject(collection="Test", properties={"name": "test"}, index=index),
    )


def _error_reference(index: int) -> ErrorReference:
    return ErrorReference(
        message="something went wrong",
        reference=BatchReference(
            from_object_collection="Test",
            from_object_uuid=uuid.uuid4(),
            from_property_name="other",
            to_object_uuid=uuid.uuid4(),
            index=index,
        ),
    )


@pytest.mark.parametrize(
    ("number_objects", "elapsed_time", "expected_sleep_time"),
    [
        (500, 0, 31),
        (100, 0, 6.2),
        (100, 2, 4.2),
        (100, -62, 68.2),
        (100, 7, 0),
        (0, 0, 0),
    ],
)
def test_rate_limited_batching_sleep_time_uses_previous_batch_size(
    number_objects: int, elapsed_time: float, expected_sleep_time: float
) -> None:
    batching = _RateLimitedBatching(requests_per_minute=1000)

    assert batching.get_sleep_time(
        number_objects=number_objects,
        elapsed_time=elapsed_time,
        base_time=62,
    ) == pytest.approx(expected_sleep_time)


def test_batch_object_return_add() -> None:
    lhs_uuids = [uuid.uuid4() for _ in range(MAX_STORED_RESULTS)]
    lhs = BatchObjectReturn(
        _all_responses=lhs_uuids,
        elapsed_seconds=0.1,
        errors={},
        has_errors=False,
        uuids=dict(e for e in enumerate(lhs_uuids)),
    )
    rhs_uuids = [uuid.uuid4() for _ in range(2)]
    rhs = BatchObjectReturn(
        _all_responses=rhs_uuids,
        elapsed_seconds=0.1,
        errors={},
        has_errors=False,
        uuids={
            MAX_STORED_RESULTS: rhs_uuids[0],
            MAX_STORED_RESULTS + 1: rhs_uuids[1],
        },
    )
    result = lhs + rhs
    assert len(result.all_responses) == MAX_STORED_RESULTS
    assert len(result.uuids) == MAX_STORED_RESULTS
    assert result.uuids == {
        idx + len(rhs_uuids): v
        for idx, v in enumerate(lhs_uuids[len(rhs_uuids) : MAX_STORED_RESULTS] + rhs_uuids)
    }


def test_batch_object_return_has_errors_when_constructed_with_errors() -> None:
    err = _error_object(0)
    result = BatchObjectReturn(_all_responses=[err], errors={0: err})
    assert result.has_errors


def test_batch_object_return_add_sets_has_errors() -> None:
    err = _error_object(1)
    result = BatchObjectReturn()
    result += BatchObjectReturn(_all_responses=[uuid.uuid4()], uuids={0: uuid.uuid4()})
    result += BatchObjectReturn(_all_responses=[err], errors={1: err})
    assert result.has_errors
    assert len(result.errors) == 1


def test_batch_object_return_has_no_errors_when_all_succeed() -> None:
    uid = uuid.uuid4()
    result = BatchObjectReturn()
    result += BatchObjectReturn(_all_responses=[uid], uuids={0: uid})
    assert not result.has_errors


def test_batch_reference_return_has_errors_when_constructed_with_errors() -> None:
    err = _error_reference(0)
    result = BatchReferenceReturn(errors={0: err})
    assert result.has_errors


def test_batch_reference_return_add_sets_has_errors() -> None:
    err = _error_reference(0)
    result = BatchReferenceReturn()
    result += BatchReferenceReturn(errors={0: err})
    assert result.has_errors
    assert len(result.errors) == 1


def test_validate_props_raises_for_top_level_id() -> None:
    with pytest.raises(WeaviateInsertInvalidPropertyError):
        _validate_props({"id": "abc123"})


def test_validate_props_allows_nested_id() -> None:
    _validate_props({"id": "abc123"}, nested=True)


def test_validate_props_raises_for_top_level_vector() -> None:
    with pytest.raises(WeaviateInsertInvalidPropertyError):
        _validate_props({"vector": [0.1, 0.2]})


def test_validate_props_raises_for_nested_vector() -> None:
    with pytest.raises(WeaviateInsertInvalidPropertyError):
        _validate_props({"vector": [0.1, 0.2]}, nested=True)


def _collect_one_of_everything(collected: _BatchDataWrapper) -> _BatchDataWrapper:
    """Fill a batch's internal results the way a partially failed run would."""
    err_obj = _error_object(0)
    err_ref = _error_reference(0)
    collected.failed_objects.append(err_obj)
    collected.failed_references.append(err_ref)
    collected.results.objs += BatchObjectReturn(_all_responses=[err_obj], errors={0: err_obj})
    collected.results.refs += BatchReferenceReturn(errors={0: err_ref})
    collected.imported_shards.add(Shard(collection="Test"))
    return collected


def _assert_published(published: _BatchDataWrapper, collected: _BatchDataWrapper) -> None:
    """Assert that everything gathered so far reached the public accessors, as a snapshot."""
    assert len(published.failed_objects) == 1
    assert len(published.failed_references) == 1
    assert published.results.objs.has_errors
    assert published.results.refs.has_errors
    assert published.imported_shards == {Shard(collection="Test")}

    # The background workers outlive an interrupted shutdown, so what was published has to be
    # a snapshot: a user who prints `len(batch.failed_objects)` and then builds a frame from
    # the same property in the next cell must not get two different answers.
    collected.failed_objects.append(_error_object(1))
    collected.failed_references.append(_error_reference(1))
    collected.imported_shards.add(Shard(collection="Other"))
    # `BatchObjectReturn.__add__` mutates the left-hand side, so this also catches a `results`
    # that was handed over by reference instead of rebuilt.
    collected.results.objs += BatchObjectReturn(errors={1: _error_object(1)})
    collected.results.refs += BatchReferenceReturn(errors={1: _error_reference(1)})
    assert len(published.failed_objects) == 1
    assert len(published.failed_references) == 1
    assert published.imported_shards == {Shard(collection="Test")}
    assert len(published.results.objs.errors) == 1
    assert len(published.results.refs.errors) == 1


def _bare_batch(published: _BatchDataWrapper) -> _BatchBase:
    """Build a `_BatchBase` carrying only the state that `_shutdown` touches.

    `_BatchBase.__init__` needs a live connection and starts background threads, neither of
    which belongs in a unit test, so the handful of attributes `_shutdown` uses are set
    directly. The `_BatchBase__` prefixes are what Python's name mangling turns the
    `__`-private names into.
    """
    batch = object.__new__(_BatchBase)
    # The wrapper the public `batch.failed_objects` / `batch.results` accessors read.
    batch._BatchBase__results_for_wrapper_backup = published
    # The wrapper the batch itself collects into while it runs.
    batch._BatchBase__results_for_wrapper = _BatchDataWrapper()
    batch._BatchBase__results_lock = threading.Lock()
    batch._BatchBase__shut_background_thread_down = threading.Event()
    # A thread that was never started is never alive, so `_shutdown`'s wait loop is a no-op.
    batch._BatchBase__bg_threads = threading.Thread(target=lambda: None)
    return batch


def _bare_stream_batch(
    published: _BatchDataWrapper, join: Callable[[float], None]
) -> _BatchBaseSync:
    """Build a `_BatchBaseSync` (the `batch.stream()` colour) carrying only what `_wait` reads."""
    batch = object.__new__(_BatchBaseSync)
    batch._BatchBaseSync__results_for_wrapper_backup = published
    batch._BatchBaseSync__results_for_wrapper = _BatchDataWrapper()
    batch._BatchBaseSync__results_lock = threading.Lock()
    batch._BatchBaseSync__connection = SimpleNamespace(timeout_config=SimpleNamespace(insert=1))
    batch._BatchBaseSync__bg_threads = SimpleNamespace(join=join)
    return batch


def _bare_stream_batch_async(
    published: _BatchDataWrapper, gather: Callable[..., Awaitable[None]]
) -> _BatchBaseAsync:
    """Build a `_BatchBaseAsync` (the only colour the async client exposes) for `_wait`."""
    batch = object.__new__(_BatchBaseAsync)
    batch._BatchBaseAsync__results_for_wrapper_backup = published
    batch._BatchBaseAsync__results_for_wrapper = _BatchDataWrapper()
    batch._BatchBaseAsync__connection = SimpleNamespace(timeout_config=SimpleNamespace(insert=1))
    batch._BatchBaseAsync__bg_tasks = SimpleNamespace(gather=gather)
    return batch


def _interrupt_main_with_sigint() -> None:
    """Send a real SIGINT to this process and wait for the interpreter to act on it.

    `os.kill` only trips a flag in the C signal handler; CPython turns that into a
    `KeyboardInterrupt` in the main thread at the next bytecode boundary, which the sleep
    loop below is guaranteed to reach. That is the same path a Ctrl-C takes in a notebook.
    """
    os.kill(os.getpid(), signal.SIGINT)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        time.sleep(0.01)
    raise AssertionError("SIGINT did not raise KeyboardInterrupt in the main thread")


@pytest.fixture
def default_sigint_handler() -> Iterator[None]:
    """Make SIGINT raise `KeyboardInterrupt` regardless of what the test runner installed."""
    previous = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


needs_sigint = pytest.mark.skipif(
    sys.platform == "win32",
    reason="os.kill cannot deliver SIGINT to the current process on Windows",
)


@needs_sigint
def test_shutdown_publishes_results_when_interrupted(default_sigint_handler: None) -> None:
    published = _BatchDataWrapper()
    batch = _bare_batch(published)
    collected = _collect_one_of_everything(batch._BatchBase__results_for_wrapper)
    batch.flush = _interrupt_main_with_sigint  # type: ignore[method-assign]

    with pytest.raises(KeyboardInterrupt):
        batch._shutdown()

    _assert_published(published, collected)
    # The interrupt unwound out of `flush()` before the batch asked its daemon threads to
    # stop, so `_shutdown` has to ask on the way out: otherwise they keep uploading the batch
    # the user just aborted, and a notebook that retries leaks a pair of them per attempt.
    assert batch._BatchBase__shut_background_thread_down.is_set()


def test_shutdown_publishes_results_on_a_clean_exit() -> None:
    published = _BatchDataWrapper()
    batch = _bare_batch(published)
    collected = _collect_one_of_everything(batch._BatchBase__results_for_wrapper)
    batch.flush = lambda: None  # type: ignore[method-assign]

    batch._shutdown()

    _assert_published(published, collected)
    assert batch._BatchBase__shut_background_thread_down.is_set()


@needs_sigint
def test_stream_wait_publishes_results_when_interrupted(default_sigint_handler: None) -> None:
    published = _BatchDataWrapper()
    batch = _bare_stream_batch(published, join=lambda _timeout: _interrupt_main_with_sigint())
    collected = _collect_one_of_everything(batch._BatchBaseSync__results_for_wrapper)

    with pytest.raises(KeyboardInterrupt):
        batch._wait()

    _assert_published(published, collected)


def test_stream_wait_publishes_results_on_a_clean_exit() -> None:
    published = _BatchDataWrapper()
    batch = _bare_stream_batch(published, join=lambda _timeout: None)
    collected = _collect_one_of_everything(batch._BatchBaseSync__results_for_wrapper)

    batch._wait()

    _assert_published(published, collected)


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, asyncio.CancelledError])
def test_stream_wait_async_publishes_results_when_interrupted(
    interrupt: type[BaseException],
) -> None:
    # A Ctrl-C in a notebook cell that is awaiting reaches the coroutine as a CancelledError
    # thrown in at the await point; `asyncio.run` in a script surfaces the KeyboardInterrupt
    # itself. Both are BaseExceptions, so only a `finally` catches them.
    async def gather(timeout: float) -> None:
        raise interrupt()

    published = _BatchDataWrapper()
    batch = _bare_stream_batch_async(published, gather=gather)
    collected = _collect_one_of_everything(batch._BatchBaseAsync__results_for_wrapper)

    with pytest.raises(interrupt):
        asyncio.run(batch._wait())

    _assert_published(published, collected)


def test_stream_wait_async_publishes_results_on_a_clean_exit() -> None:
    async def gather(timeout: float) -> None:
        return None

    published = _BatchDataWrapper()
    batch = _bare_stream_batch_async(published, gather=gather)
    collected = _collect_one_of_everything(batch._BatchBaseAsync__results_for_wrapper)

    asyncio.run(batch._wait())

    _assert_published(published, collected)
