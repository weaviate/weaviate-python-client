"""Unit tests for the async batch-stream failure handling.

These pin three behaviors added for WASM/background-failure robustness without needing
a cluster: the grpc-web fail-fast in _start, flush() raising instead of spinning
forever, and _wait() preserving partial results while still raising.
"""

import asyncio

import grpc
import pytest

from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.collections.batch.base import _BatchDataWrapper
from weaviate.exceptions import WeaviateBatchStreamError


def _bare_batch(**mangled) -> _BatchBaseAsync:
    batch = object.__new__(_BatchBaseAsync)
    for name, value in mangled.items():
        setattr(batch, f"_BatchBaseAsync__{name}", value)
    return batch


def test_start_fails_fast_when_grpc_web_shim_active(monkeypatch) -> None:
    # over grpc-web the BatchStream RPC would die inside the background tasks (silent
    # drop / endless flush); _start must raise before any task is created
    monkeypatch.setattr(grpc, "__weaviate_grpc_web_shim__", True, raising=False)
    batch = _bare_batch()  # the guard runs before any attribute access
    with pytest.raises(WeaviateBatchStreamError, match="insert_many"):
        asyncio.run(batch._start())


def test_flush_raises_background_exception_instead_of_hanging() -> None:
    # with dead background tasks nothing drains the queues; flush used to spin on
    # asyncio.sleep(0.01) forever
    batch = _bare_batch(
        bg_exception=RuntimeError("boom"),
        batch_objects=[object()],
        batch_references=[],
    )

    async def flush_with_deadline() -> None:
        await asyncio.wait_for(batch.flush(), timeout=2)

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(flush_with_deadline())


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
