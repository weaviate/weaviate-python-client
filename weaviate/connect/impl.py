import inspect
from functools import wraps
from types import FunctionType
from typing import Any, Awaitable, Callable, List, Tuple, TypeVar

from weaviate.connect.executor import Colour

T = TypeVar("T")


def no_wrapping(func: T) -> T:
    func.__setattr__("__no_wrapping__", True)
    return func


def wrap(colour: Colour) -> Callable[[T], T]:
    def decorator(cls: T) -> T:
        # Find all abstract methods in the async class
        methods: List[Tuple[str, FunctionType]] = []
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            # pulls the original method if it was wrapped by functools.wraps, e.g. @deprecated
            method = getattr(method, "__wrapped__", method)

            if name.startswith("_"):
                continue

            methods.append((name, method))

        # Create sync versions of the async methods
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
