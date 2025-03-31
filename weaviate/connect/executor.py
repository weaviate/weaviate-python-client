import inspect
from functools import wraps
from types import FunctionType
from typing import Awaitable, Callable, List, Literal, Tuple, TypeVar, Union, Any, overload, cast
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

Result = Union[T, Awaitable[T]]
Colour = Literal["async", "sync"]


def raise_exception(e: Exception) -> Any:
    raise e


@overload
def execute(
    method: Callable[P, Awaitable[R]],
    response_callback: Callable[[R], T],
    exception_callback: Callable[[Exception], Any] = raise_exception,
    *args: P.args,
    **kwargs: P.kwargs,
) -> Awaitable[T]: ...


@overload
def execute(
    method: Callable[P, R],
    response_callback: Callable[[R], T],
    exception_callback: Callable[[Exception], Any] = raise_exception,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T: ...


@overload
def execute(
    method: SyncOrAsyncMethod[P, R],
    response_callback: Callable[[R], T],
    exception_callback: Callable[[Exception], Any] = raise_exception,
    *args: P.args,
    **kwargs: P.kwargs,
) -> Union[T, Awaitable[T]]: ...


def execute(
    method: SyncOrAsyncMethod[P, R],
    response_callback: SyncOrAsyncCallback[R, T, A],
    exception_callback: Callable[[Exception], Any] = raise_exception,
    *args: P.args,
    **kwargs: P.kwargs,
) -> Union[T, Awaitable[T], Awaitable[A]]:
    # wrap method call in try-except to catch exceptions for sync method
    try:
        call = method(*args, **kwargs)
        if isinstance(call, Awaitable):

            async def _execute() -> T:
                # wrap await in try-except to catch exceptions for async method
                try:
                    res = await call
                    res_call = response_callback(res)
                    if not isinstance(res_call, Awaitable):
                        return res_call
                    return cast(T, await res_call)
                except Exception as e:
                    return cast(T, exception_callback(e))

            return _execute()
        resp_call = response_callback(call)
        assert not isinstance(resp_call, Awaitable)
        return resp_call
    except Exception as e:
        return cast(T, exception_callback(e))


def result(result: Result[T]) -> T:
    assert not isinstance(result, Awaitable), f"Expected sync result, got {result}"
    return result


async def aresult(result: Result[T]) -> T:
    assert isinstance(result, Awaitable), f"Expected async result, got {result}"
    return await result


def return_(value: T, colour: Colour) -> Result[T]:
    if colour == "async":

        async def execute_() -> T:
            return value

        return execute_()
    return value


def empty(colour: Colour) -> Result[None]:
    return return_(None, colour)


def do_nothing(value: T) -> T:
    return value


T = TypeVar("T")


def no_wrapping(func: T) -> T:
    func.__setattr__("__no_wrapping__", True)
    return func


def wrap(colour: Colour) -> Callable[[T], T]:
    def decorator(cls: T) -> T:
        methods: List[Tuple[str, FunctionType]] = []
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            # pulls the original method if it was wrapped by functools.wraps, e.g. @deprecated
            method = getattr(method, "__wrapped__", method)

            if name.startswith("_"):
                continue

            methods.append((name, method))

        # loop through all executor methods and wrap them either as sync or async
        # depending on the colour passed to the decorator
        # if the method has been marked with @no_wrapping, skip it
        # this is used for methods that are always sync, i.e. do no I/O, but still
        # need to be inherited from the base executor class
        for name, method in methods:
            if getattr(method, "__no_wrapping__", method):
                continue

            if colour == "async":

                @wraps(method)
                async def wrapped_method_async(
                    self,
                    *args,
                    method: FunctionType = method,
                    **kwargs,
                ) -> Any:
                    result = method(self, *args, **kwargs)
                    assert isinstance(result, Awaitable)
                    return await result

                setattr(cls, name, wrapped_method_async)
            else:

                @wraps(method)
                def wrapped_method_sync(
                    self,
                    *args,
                    method: FunctionType = method,
                    **kwargs,
                ) -> Any:
                    result = method(self, *args, **kwargs)
                    assert not isinstance(result, Awaitable)
                    return result

                setattr(cls, name, wrapped_method_sync)
        return cls

    return decorator
