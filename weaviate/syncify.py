import asyncio
import inspect
from dataclasses import dataclass
from functools import wraps
from types import MappingProxyType, FunctionType
from typing import Any, Awaitable, Callable, List, Type, TypeVar

from weaviate.event_loop import _EventLoopSingleton

C = TypeVar("C")


def convert(cls: C) -> C:
    """
    Class decorator that converts async methods to sync methods preserving all overloads and documentation.
    """
    for name, method in cls.__bases__[0].__dict__.items():  # type: ignore
        original_method = method

        if hasattr(method, "__wrapped__"):
            method = method.__wrapped__

        if asyncio.iscoroutinefunction(method) and not name.startswith("_"):
            new_name = "__" + name
            setattr(cls, new_name, method)

            # Create a new sync method that wraps the async method
            @wraps(original_method)  # type: ignore
            def sync_method(self, *args, __new_name=new_name, **kwargs):
                async_func = getattr(cls, __new_name)
                return _EventLoopSingleton.get_instance().run_until_complete(
                    async_func, self, *args, **kwargs
                )

            setattr(cls, name, sync_method)
    return cls


T = TypeVar("T")


@dataclass
class _Meta:
    name: str
    parameters: MappingProxyType[str, inspect.Parameter]
    async_: FunctionType


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
        metadata: List[_Meta] = []
        for name, method in inspect.getmembers(async_cls, inspect.isfunction):
            # pulls the original method if it was wrapped by functools.wraps, e.g. @deprecated
            method = getattr(method, "__wrapped__", method)

            if name.startswith("__"):
                continue

            if inspect.iscoroutinefunction(method):
                metadata.append(
                    _Meta(name=name, async_=method, parameters=inspect.signature(method).parameters)
                )

        # Create sync versions of the async methods
        for metadatum in metadata:

            @wraps(metadatum.async_)
            def sync_method(  # type: ignore
                self,
                *args,
                meta: _Meta = metadatum,
                **kwargs,
            ) -> Any:
                # Have to get the executor within the method so that any classes that have to
                # instantiate _executor in their __init__ files, e.g. _DataCollection, because of
                # tenant/consistency_level injection, can do so without being None here.
                executor = getattr(self, "_executor", None)
                if executor is None:
                    raise AttributeError("Executor not found in sync class")
                executor_method = getattr(executor, meta.name, None)
                if executor_method is None:
                    raise AttributeError(f"Method {meta.name} not found in executor")
                for index, (name, param) in enumerate(meta.parameters.items()):
                    if name == "self":
                        continue
                    if (
                        param.kind == inspect.Parameter.KEYWORD_ONLY
                        and name not in kwargs
                        and param.default is not inspect.Parameter.empty
                    ):
                        kwargs[name] = param.default
                    if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                        try:
                            # check if the argument is present as a positional arg
                            kwargs[name] = args[index - 1]  # offset the self param
                            continue
                        except IndexError:
                            # if not, then check it is present as a keyword arg
                            if name in kwargs:
                                continue
                            # if it is not present as a keyword arg, then use the default value
                            if param.default is not inspect.Parameter.empty:
                                kwargs[name] = param.default
                                continue
                            # otherwise, throw an exception
                            raise TypeError(f"Missing required argument '{name}'")

                result = executor_method(**kwargs, connection=self._connection)
                assert not isinstance(result, Awaitable)
                return result

            # Add method docstring
            if metadatum.async_.__doc__:
                sync_method.__doc__ = metadatum.async_.__doc__

            # Add the sync method to the sync class
            setattr(sync_cls, metadatum.name, sync_method)
        return sync_cls

    return decorator
