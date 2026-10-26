from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call
from uuid import UUID

import pytest

from weaviate.collections.iterator import _IteratorInputs, _ObjectAIterator, _ObjectIterator


def _inputs():
    return _IteratorInputs(
        include_vector=True,
        return_metadata=None,
        return_properties=["title"],
        return_references=None,
        after=str(UUID(int=1)),
    )


@pytest.mark.parametrize("initially_empty", [False, True])
def test_iterator_stays_exhausted_until_restarted(initially_empty):
    obj = SimpleNamespace(uuid=UUID(int=2))
    earlier_obj = SimpleNamespace(uuid=UUID(int=3))
    first_page = [] if initially_empty else [earlier_obj, obj]
    pages = [SimpleNamespace(objects=first_page)]
    if not initially_empty:
        pages.append(SimpleNamespace(objects=[]))
    pages.append(SimpleNamespace(objects=[obj]))
    query = Mock()
    query.fetch_objects.side_effect = pages
    iterator = _ObjectIterator(query, _inputs(), cache_size=5)
    iter(iterator)

    if not initially_empty:
        assert next(iterator) is earlier_obj
        assert next(iterator) is obj
        assert query.fetch_objects.call_count == 1
    with pytest.raises(StopIteration):
        next(iterator)
    terminal_call_count = query.fetch_objects.call_count
    for _ in range(2):
        with pytest.raises(StopIteration):
            next(iterator)
    assert query.fetch_objects.call_count == terminal_call_count
    assert query.fetch_objects.call_args_list[0] == call(
        limit=5,
        after=UUID(int=1),
        include_vector=True,
        return_metadata=None,
        return_properties=["title"],
        return_references=None,
    )
    if not initially_empty:
        assert query.fetch_objects.call_args.kwargs["after"] == obj.uuid

    iter(iterator)
    assert next(iterator) is obj
    assert query.fetch_objects.call_args.kwargs["after"] == UUID(int=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("initially_empty", [False, True])
async def test_async_iterator_stays_exhausted_until_restarted(initially_empty):
    obj = SimpleNamespace(uuid=UUID(int=2))
    earlier_obj = SimpleNamespace(uuid=UUID(int=3))
    first_page = [] if initially_empty else [earlier_obj, obj]
    pages = [SimpleNamespace(objects=first_page)]
    if not initially_empty:
        pages.append(SimpleNamespace(objects=[]))
    pages.append(SimpleNamespace(objects=[obj]))
    query = Mock()
    query.fetch_objects = AsyncMock(side_effect=pages)
    iterator = _ObjectAIterator(query, _inputs(), cache_size=5)
    iterator.__aiter__()

    if not initially_empty:
        assert await iterator.__anext__() is earlier_obj
        assert await iterator.__anext__() is obj
        assert query.fetch_objects.await_count == 1
    with pytest.raises(StopAsyncIteration):
        await iterator.__anext__()
    terminal_call_count = query.fetch_objects.await_count
    for _ in range(2):
        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()
    assert query.fetch_objects.await_count == terminal_call_count
    assert query.fetch_objects.call_args_list[0] == call(
        limit=5,
        after=UUID(int=1),
        include_vector=True,
        return_metadata=None,
        return_properties=["title"],
        return_references=None,
    )
    if not initially_empty:
        assert query.fetch_objects.call_args.kwargs["after"] == obj.uuid

    iterator.__aiter__()
    assert await iterator.__anext__() is obj
    assert query.fetch_objects.call_args.kwargs["after"] == UUID(int=1)
