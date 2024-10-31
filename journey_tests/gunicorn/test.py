import httpx


def test_sync_in_sync() -> None:
    res = httpx.get("http://localhost:8000/sync-in-sync")
    assert res.status_code == 200
    assert len(res.json()) == 100


def test_sync_in_async() -> None:
    res = httpx.get("http://localhost:8000/sync-in-async")
    assert res.status_code == 200
    assert len(res.json()) == 100


def test_async_in_async() -> None:
    res = httpx.get("http://localhost:8000/async-in-async")
    assert res.status_code == 200
    assert len(res.json()) == 100
