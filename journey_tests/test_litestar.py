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


@get("/sync", sync_to_thread=True)
def sync(state: MyState) -> dict:
    return state.sync.simple()


@get("/async")
async def async_(state: MyState) -> dict:
    return await state.async_.simple()


app = Litestar(route_handlers=[sync, async_], lifespan=[lifespan])


def test_sync() -> None:
    with TestClient(app=app) as client:
        res = client.get("/sync")
        assert res.status_code == 200
        assert len(res.json()) == 100


def test_async() -> None:
    with TestClient(app=app) as client:
        res = client.get("/async")
        assert res.status_code == 200
        assert len(res.json()) == 100
