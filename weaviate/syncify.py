import asyncio
import inspect
from functools import wraps
from typing import Any, Awaitable, Callable, Type, TypeVar, get_type_hints

from weaviate.event_loop import _EventLoopSingleton

C = TypeVar("C")


def convert(cls: C) -> C:
    """
    Class decorator that converts async methods to sync methods preserving all overloads and documentation.
    """
    for name, method in cls.__bases__[0].__dict__.items():  # type: ignore
        if asyncio.iscoroutinefunction(method) and not name.startswith("_"):
            new_name = "__" + name
            setattr(cls, new_name, method)

            # Create a new sync method that wraps the async method
            @wraps(method)  # type: ignore
            def sync_method(self, *args, __new_name=new_name, **kwargs):
                async_func = getattr(cls, __new_name)
                return _EventLoopSingleton.get_instance().run_until_complete(
                    async_func, self, *args, **kwargs
                )

            setattr(cls, name, sync_method)
    return cls


T = TypeVar("T")


def convert_new(async_cls: Type[T]) -> Callable[[Type], Type]:
    """
    Class decorator that generates a synchronous version of an async class.
    It takes an async class as input and applies the decorator to create a
    synchronous version of the class with the same methods.

    Usage:
        @async_to_sync_class(_DebugAsync)
        class _Debug:
            pass
    """

    def decorator(sync_cls: Type) -> Type:
        # Copy docstring from async class
        if async_cls.__doc__:
            sync_cls.__doc__ = async_cls.__doc__

        # Find all async methods in the async class
        async_methods = {}
        for name, method in inspect.getmembers(async_cls, inspect.isfunction):
            if name.startswith("__"):
                continue

            if inspect.iscoroutinefunction(method):
                async_methods[name] = method

        # Create sync versions of the async methods
        for name, async_method in async_methods.items():
            # Get type hints from the async method
            # type_hints = get_type_hints(async_method)
            # return_type = type_hints.get('return', Any)

            executor = getattr(sync_cls, "_executor", None)
            if executor is None:
                raise AttributeError("Executor not found in sync class")
            executor_method = getattr(executor, name, None)
            if executor_method is None:
                raise AttributeError(f"Method {name} not found in executor")

            # Create a sync version of the method
            @wraps(async_method)
            def sync_method(self, *args, **kwargs):
                assert executor_method is not None
                result = executor_method(*args, **kwargs, connection=self._connection)
                assert not isinstance(result, Awaitable)
                return result

            # Add method docstring
            if async_method.__doc__:
                sync_method.__doc__ = async_method.__doc__

            # Add the sync method to the sync class
            setattr(sync_cls, name, sync_method)

        return sync_cls

    return decorator
