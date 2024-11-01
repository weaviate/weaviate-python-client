from contextlib import asynccontextmanager

from litestar import Litestar, get
from litestar.datastructures import State
from litestar.testing import TestClient

from journey_tests.journeys import AsyncJourneys, SyncJourneys


class MyState(State):
    sync: SyncJourneys
    async_: AsyncJourneys


@asynccontextmanager
async def lifespan(app: Litestar):
    sync = SyncJourneys.use()
    async_ = await AsyncJourneys.use()
    app.state.sync = sync
    app.state.async_ = async_
    try:
        yield
    finally:
        sync.close()
        await async_.close()


@get("/sync-in-sync", sync_to_thread=True)
def sync_in_sync(state: MyState) -> dict:
    return state.sync.simple()


@get("/sync-in-async", sync_to_thread=True)
async def sync_in_async(state: MyState) -> dict:
    return state.sync.simple()


@get("/async-in-async")
async def async_in_async(state: MyState) -> dict:
    return await state.async_.simple()


app = Litestar(route_handlers=[sync_in_sync, sync_in_async, async_in_async], lifespan=[lifespan])


def test_sync_in_sync() -> None:
    with TestClient(app=app) as client:
        res = client.get("/sync-in-sync")
        assert res.status_code == 200
        assert len(res.json()) == 100


def test_sync_in_async() -> None:
    with TestClient(app=app) as client:
        res = client.get("/sync-in-async")
        assert res.status_code == 200
        assert len(res.json()) == 100


def test_async_in_async() -> None:
    with TestClient(app=app) as client:
        res = client.get("/async-in-async")
        assert res.status_code == 200
        assert len(res.json()) == 100
