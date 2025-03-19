from typing import Coroutine, Awaitable, Callable, TypeVar, Union, Any, overload
from typing_extensions import ParamSpec

R = TypeVar("R")
P = ParamSpec("P")
T = TypeVar("T")

ExecutorMethod = Union[
    Callable[P, R], Callable[P, Awaitable[R]], Callable[P, Union[R, Awaitable[R]]]
]


def raise_exception(e: Exception) -> Any:
    raise e


@overload
def execute(
    response_callback: Callable[[R], T],
    method: Callable[P, Awaitable[R]],
    *args: P.args,
    exception_callback: Callable[[Exception], Any] = raise_exception,
    **kwargs: P.kwargs,
) -> Awaitable[T]: ...


@overload
def execute(
    response_callback: Callable[[R], T],
    method: Callable[P, R],
    *args: P.args,
    exception_callback: Callable[[Exception], T] = raise_exception,
    **kwargs: P.kwargs,
) -> T: ...


def execute(
    response_callback: Callable[[R], T],
    method: ExecutorMethod[P, R],
    *args: P.args,
    exception_callback: Callable[[Exception], T] = raise_exception,
    **kwargs: P.kwargs,
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
            call = response_callback(res)
            assert not isinstance(call, Awaitable)
            return call
        except Exception as e:
            raise exception_callback(e)


ExecutorResult = Union[T, Awaitable[T]]
