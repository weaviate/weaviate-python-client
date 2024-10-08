from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from journey_tests.journeys import AsyncJourneys, SyncJourneys


class Journeys(TypedDict):
    sync: SyncJourneys
    async_: AsyncJourneys


journeys: Journeys = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    journeys["async_"] = await AsyncJourneys.use()
    journeys["sync"] = SyncJourneys.use()
    try:
        yield
    finally:
        await journeys["async_"].close()
        journeys["sync"].close()


app = FastAPI(lifespan=lifespan)


@app.get("/sync-in-sync")
def sync_in_sync() -> JSONResponse:
    return JSONResponse(content=journeys["sync"].simple())


@app.get("/sync-in-async")
async def sync_in_async() -> JSONResponse:
    return JSONResponse(content=journeys["sync"].simple())


@app.get("/async-in-async")
async def async_in_async() -> JSONResponse:
    return JSONResponse(content=await journeys["async_"].simple())


def test_sync_in_sync() -> None:
    with TestClient(app) as client:
        res = client.get("/sync-in-sync")
        assert res.status_code == 200
        assert len(res.json()) == 100


def test_sync_in_async() -> None:
    with TestClient(app) as client:
        res = client.get("/sync-in-async")
        assert res.status_code == 200
        assert len(res.json()) == 100


def test_async_in_async() -> None:
    with TestClient(app) as client:
        res = client.get("/async-in-async")
        assert res.status_code == 200
        assert len(res.json()) == 100
