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


@app.get("/sync")
def sync() -> JSONResponse:
    return JSONResponse(content=journeys["sync"].simple())


@app.get("/async")
async def async_() -> JSONResponse:
    return JSONResponse(content=await journeys["async_"].simple())


def test_sync() -> None:
    with TestClient(app) as client:
        res = client.get("/sync")
        assert res.status_code == 200
        assert len(res.json()) == 100


def test_async() -> None:
    with TestClient(app) as client:
        res = client.get("/async")
        assert res.status_code == 200
        assert len(res.json()) == 100
