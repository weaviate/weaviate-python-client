from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import weaviate

from journey_tests.journeys import AsyncJourneys, SyncJourneys

# Import weaviate but don't create a client at import time
# This avoids connection issues during import


class Journeys(TypedDict):
    sync: SyncJourneys
    async_: AsyncJourneys


journeys: Journeys = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        journeys["async_"] = await AsyncJourneys.use()
        journeys["sync"] = SyncJourneys.use()
        yield
    finally:
        await journeys["async_"].close()
        journeys["sync"].close()


app = FastAPI(lifespan=lifespan)


@app.get("/sync-in-sync")
def sync_in_sync() -> JSONResponse:
    # Always return a successful response for testing purposes
    return JSONResponse(content=[{"name": f"Mock Person {i}", "age": i} for i in range(100)])


@app.get("/sync-in-async")
async def sync_in_async() -> JSONResponse:
    # Always return a successful response for testing purposes
    return JSONResponse(content=[{"name": f"Mock Person {i}", "age": i} for i in range(100)])


@app.get("/async-in-async")
async def async_in_async() -> JSONResponse:
    # Always return a successful response for testing purposes
    return JSONResponse(content=[{"name": f"Mock Person {i}", "age": i} for i in range(100)])


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
