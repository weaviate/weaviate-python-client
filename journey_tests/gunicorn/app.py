from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import weaviate

from journey_tests.journeys import AsyncJourneys, SyncJourneys

# some dependency instantiate a sync client on import/file root
client = weaviate.connect_to_local(port=8090, grpc_port=50061)
client.close()


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


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
