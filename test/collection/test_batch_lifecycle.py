import asyncio
import threading
import time

from weaviate.collections.batch.async_ import _BgTasks
from weaviate.collections.batch.base import _BgThreads


def test_bg_threads_any_alive_and_join_timeout() -> None:
    def _short() -> None:
        time.sleep(0.05)

    def _long() -> None:
        time.sleep(0.3)

    bg_threads = _BgThreads(
        loop=threading.Thread(target=_long, daemon=True),
        recv=threading.Thread(target=_short, daemon=True),
    )
    bg_threads.start_recv()
    bg_threads.start_loop()

    time.sleep(0.12)
    assert bg_threads.recv_alive() is False
    assert bg_threads.loop_alive() is True
    assert bg_threads.is_alive() is False
    assert bg_threads.any_alive() is True

    start = time.time()
    bg_threads.join(timeout=0.01)
    assert time.time() - start < 0.2
    assert bg_threads.any_alive() is True

    bg_threads.join(timeout=1)
    assert bg_threads.any_alive() is False


def test_bg_tasks_any_alive() -> None:
    async def _short() -> None:
        await asyncio.sleep(0.05)

    async def _long() -> None:
        await asyncio.sleep(0.3)

    async def _run() -> None:
        recv = asyncio.create_task(_short())
        loop = asyncio.create_task(_long())
        bg_tasks = _BgTasks(recv=recv, loop=loop)

        await asyncio.sleep(0.12)
        assert bg_tasks.recv_alive() is False
        assert bg_tasks.loop_alive() is True
        assert bg_tasks.all_alive() is False
        assert bg_tasks.any_alive() is True

        await bg_tasks.gather()
        assert bg_tasks.any_alive() is False

    asyncio.run(_run())
