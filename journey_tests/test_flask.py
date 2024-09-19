from flask import Flask, g

from journey_tests.journeys import AsyncJourneys, SyncJourneys

app = Flask(__name__)


def get_sync_client() -> SyncJourneys:
    if "sync" not in g:
        g.sync = SyncJourneys.use()
    return g.sync


async def get_async_client() -> AsyncJourneys:
    if "async" not in g:
        g.async_ = await AsyncJourneys.use()
    return g.async_


@app.route("/sync")
def sync() -> dict:
    return get_sync_client().simple()


@app.route("/async")
async def async_() -> dict:
    return await (await get_async_client()).simple()


def test_sync() -> None:
    res = app.test_client().get("/sync")
    assert res.status_code == 200
    assert len(res.json) == 100


def test_async() -> None:
    res = app.test_client().get("/async")
    assert res.status_code == 200
    assert len(res.json) == 100
