from typing import Coroutine, Awaitable, Callable, TypeVar, Union, Any, overload, cast
from typing_extensions import ParamSpec

R = TypeVar("R")
P = ParamSpec("P")
T = TypeVar("T")
A = TypeVar("A")


SyncOrAsyncCallback = Union[
    Callable[[R], T], Callable[[R], Awaitable[A]], Callable[[R], Union[T, Awaitable[A]]]
]

SyncOrAsyncMethod = Union[
    Callable[P, R], Callable[P, Awaitable[R]], Callable[P, Union[R, Awaitable[R]]]
]

ExecutorResult = Union[T, Awaitable[T]]


def raise_exception(e: Exception) -> Any:
    raise e


@overload
def execute(
    response_callback: Callable[[R], Awaitable[A]],
    method: Callable[P, Awaitable[R]],
    *args: P.args,
    exception_callback: Callable[[Exception], Any] = raise_exception,
    **kwargs: P.kwargs,
) -> Awaitable[A]: ...


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
    response_callback: SyncOrAsyncCallback[R, T, A],
    method: SyncOrAsyncMethod[P, R],
    *args: P.args,
    exception_callback: Callable[[Exception], T] = raise_exception,
    **kwargs: P.kwargs,
) -> Union[T, Awaitable[T], Awaitable[A]]:
    call = method(*args, **kwargs)
    if isinstance(call, Awaitable):

        async def _execute() -> T:
            try:
                res = await call
                res_call = response_callback(res)
                if not isinstance(res_call, Awaitable):
                    return res_call
                return cast(T, await res_call)
            except Exception as e:
                return exception_callback(e)

        return _execute()
    else:
        res = call
        try:
            res_call = response_callback(res)
            assert not isinstance(res_call, Awaitable)
            return res_call
        except Exception as e:
            raise exception_callback(e)
