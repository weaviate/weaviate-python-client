import asyncio
import threading
import time
from concurrent.futures import Future
from typing import Any, Callable, Coroutine, Dict, Generic, Optional, TypeVar, cast

from typing_extensions import ParamSpec

from weaviate.exceptions import WeaviateClosedClientError

P = ParamSpec("P")
T = TypeVar("T")


class _Future(Future, Generic[T]):
    def result(self, timeout: Optional[float] = None) -> T:
        return cast(T, super().result(timeout))


class _EventLoop:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.loop = loop

    def start(self) -> None:
        if self.loop is not None:
            return
        self.loop = self.__start_new_event_loop()

    def run_until_complete(
        self, f: Callable[P, Coroutine[Any, Any, T]], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        """This method runs the provided coroutine in a blocking manner by scheduling its execution
        in an event loop running in a parallel thread.

        The result of the coroutine is returned, either when the coroutine completes or raises an exception.
        """
        if self.loop is None or self.loop.is_closed():
            raise WeaviateClosedClientError()
        fut = asyncio.run_coroutine_threadsafe(f(*args, **kwargs), self.loop)
        return fut.result()

    def schedule(
        self, f: Callable[P, Coroutine[Any, Any, T]], *args: P.args, **kwargs: P.kwargs
    ) -> _Future[T]:
        """This method schedules the provided coroutine for execution in the event loop running in a parallel thread.

        The coroutine will be executed asynchronously in the background.
        """
        if self.loop is None or self.loop.is_closed():
            raise WeaviateClosedClientError()
        return cast(_Future[T], asyncio.run_coroutine_threadsafe(f(*args, **kwargs), self.loop))

    def shutdown(self) -> None:
        if self.loop is None:
            return
        self.loop.call_soon_threadsafe(self.loop.stop)

    @staticmethod
    def __run_event_loop(loop: asyncio.AbstractEventLoop) -> None:
        try:
            loop.run_forever()
        finally:
            # This is entered when loop.stop is scheduled from the main thread
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    @staticmethod
    def __start_new_event_loop() -> asyncio.AbstractEventLoop:
        loop = asyncio.new_event_loop()

        event_loop = threading.Thread(
            target=_EventLoop.__run_event_loop,
            daemon=True,
            args=(loop,),
            name="eventLoop",
        )
        event_loop.start()

        while not loop.is_running():
            time.sleep(0.01)

        return loop

    @staticmethod
    def patch_exception_handler(loop: asyncio.AbstractEventLoop) -> None:
        """
        This patches the asyncio exception handler to ignore the `BlockingIOError: [Errno 35] Resource temporarily unavailable` error
        that is emitted by `aio.grpc` when multiple event loops are used in separate threads. This error is not actually an implementation/call error,
        it's just a problem with grpc's cython implementation of `aio.Channel.__init__` whereby a `socket.recv(1)` call only works on the first call with
        all subsequent calls to `aio.Channel.__init__` throwing the above error.

        This call within the `aio.Channel.__init__` method does not affect the functionality of the library and can be safely ignored.

        Context:
            - https://github.com/grpc/grpc/issues/25364
            - https://github.com/grpc/grpc/pull/36096
        """

        def exception_handler(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
            if "exception" in context:
                err = f"{type(context['exception']).__name__}: {context['exception']}"
                if "BlockingIOError: [Errno 35] Resource temporarily unavailable" == err:
                    return
            loop.default_exception_handler(context)

        loop.set_exception_handler(exception_handler)

    def __del__(self) -> None:
        self.shutdown()


class _EventLoopSingleton:
    _instance: Optional[_EventLoop] = None

    @classmethod
    def get_instance(cls) -> _EventLoop:
        if cls._instance is not None:
            return cls._instance
        cls._instance = _EventLoop()
        cls._instance.start()
        return cls._instance

    def __del__(self) -> None:
        if self._instance is not None:
            self._instance.shutdown()
            self._instance = None
