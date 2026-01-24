import asyncio
import datetime
import time
from typing import Awaitable, Callable, cast

from grpc import Call, RpcError, StatusCode  # type: ignore
from grpc.aio import AioRpcError  # type: ignore
from typing_extensions import ParamSpec, TypeVar

from weaviate.config import RetryConfig
from weaviate.exceptions import WeaviateRetryError
from weaviate.logger import logger

P = ParamSpec("P")
T = TypeVar("T")


class _Retry:
    def __init__(self, retry_config: RetryConfig) -> None:
        self.config = retry_config

    def is_retriable(self, e: Exception) -> bool:
        if isinstance(e, AioRpcError) or isinstance(e, RpcError):
            err = cast(Call, e)
            return err.code() in [
                StatusCode.UNAVAILABLE,
                StatusCode.NOT_FOUND,
                StatusCode.DEADLINE_EXCEEDED,
                StatusCode.ABORTED,
                StatusCode.INTERNAL,
                StatusCode.CANCELLED,
                StatusCode.ABORTED,
            ]
        return False

    async def awith_exponential_backoff(
        self,
        count: int,
        start_time: datetime.datetime,
        error: str,
        f: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        try:
            return await f(*args, **kwargs)
        except AioRpcError as e:
            if not self.is_retriable(e):
                raise e
            if (
                (datetime.datetime.now() - start_time).total_seconds() * 1000
            ) > self.config.timeout_ms:
                raise WeaviateRetryError(str(e), count) from e
            if count > self.config.request_retry_count:
                raise WeaviateRetryError(str(e), count) from e
            logger.info(
                f"{error} received exception: {e}. Retrying with exponential backoff in {2**count} seconds"
            )
            await asyncio.sleep((self.config.request_retry_backoff_ms / 1000.0) ** count)
            return await self.awith_exponential_backoff(
                count + 1, start_time, error, f, *args, **kwargs
            )

    def with_exponential_backoff(
        self,
        count: int,
        start_time: datetime.datetime,
        error: str,
        f: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        try:
            return f(*args, **kwargs)
        except Exception as e:
            if not self.is_retriable(e):
                raise e
            if (
                (datetime.datetime.now() - start_time).total_seconds() * 1000
            ) > self.config.timeout_ms:
                raise WeaviateRetryError(str(e), count) from e
            if count > self.config.request_retry_count:
                raise WeaviateRetryError(str(e), count) from e
            logger.info(
                f"{error} received exception: {e}. Retrying with exponential backoff in {2**count} seconds"
            )
            time.sleep((self.config.request_retry_backoff_ms / 1000.0) ** count)
            return self.with_exponential_backoff(count + 1, start_time, error, f, *args, **kwargs)
