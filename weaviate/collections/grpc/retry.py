import asyncio
from typing import Awaitable, Callable
from typing_extensions import ParamSpec, TypeVar

from grpc import StatusCode  # type: ignore
from grpc.aio import AioRpcError  # type: ignore

from weaviate.exceptions import WeaviateRetryError
from weaviate.logger import logger

P = ParamSpec("P")
T = TypeVar("T")


class _Retry:
    def __init__(self, n: int = 4) -> None:
        self.n = n

    async def with_exponential_backoff(
        self,
        count: int,
        error: str,
        f: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        try:
            return await f(*args, **kwargs)
        except AioRpcError as e:
            if e.code() != StatusCode.UNAVAILABLE:
                raise e
            logger.info(
                f"{error} received exception: {e}. Retrying with exponential backoff in {2**count} seconds"
            )
            await asyncio.sleep(2**count)
            if count > self.n:
                raise WeaviateRetryError(str(e), count) from e
            return await self.with_exponential_backoff(count + 1, error, f, *args, **kwargs)
