from typing import (
    Awaitable,
    Callable,
    TypeVar,
    Union,
)
from typing_extensions import ParamSpec

R = TypeVar("R")
P = ParamSpec("P")
T = TypeVar("T")

ExecutorMethod = Union[Callable[P, R], Callable[P, Awaitable[R]]]

def execute(
    response_callback: Callable[[R], T],
    exception_callback: Callable[[Exception], T],
    method: ExecutorMethod[P, R],
    *args: P.args,
    **kwargs: P.kwargs
) -> Union[T, Awaitable[T]]:
    call = method(*args, **kwargs)
    if isinstance(call, Awaitable):
        async def _execute() -> T:
            try:
                res = await call
                return response_callback(res)
            except Exception as e:
                return exception_callback(e)
        return _execute()
    else:
        res = call
        try:
            return response_callback(res)
        except Exception as e:
            raise exception_callback(e)


def raise_exception(e: Exception) -> None:
    raise e

ExecutorResult = Union[T, Awaitable[T]]