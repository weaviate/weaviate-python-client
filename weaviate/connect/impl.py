import inspect
from dataclasses import dataclass
from functools import wraps
from types import MappingProxyType, FunctionType
from typing import Any, Awaitable, Callable, Dict, List, Type, TypeVar

from weaviate.connect.executor import Colour
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync

T = TypeVar("T")


@dataclass
class _Meta:
    name: str
    parameters: MappingProxyType[str, inspect.Parameter]
    method: FunctionType


def generate(colour: Colour) -> Callable[[Type], Type]:
    def decorator(cls: Type) -> Type:
        # Find all abstract methods in the async class
        metadata: List[_Meta] = []
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            # pulls the original method if it was wrapped by functools.wraps, e.g. @deprecated
            method = getattr(method, "__wrapped__", method)

            if name.startswith("__"):
                continue

            if not getattr(method, "__isabstractmethod__", False):
                continue

            metadata.append(
                _Meta(name=name, method=method, parameters=inspect.signature(method).parameters)
            )

        # Create sync versions of the async methods
        for metadatum in metadata:
            if colour == "async":

                @wraps(metadatum.method)
                async def wrapped_method(  # type: ignore
                    self,
                    *args,
                    meta: _Meta = metadatum,
                    **kwargs,
                ) -> Any:
                    # Have to get the executor and connection within the method so that any classes that have to
                    # instantiate _executor in their __init__ files, e.g. _DataCollection, because of
                    # tenant/consistency_level injection, can do so without being None here.
                    executor = getattr(self, "_executor", None)
                    if executor is None:
                        raise AttributeError("Executor not found in sync class")
                    executor_method = getattr(executor, meta.name, None)
                    if executor_method is None:
                        raise AttributeError(f"Method {meta.name} not found in executor")

                    connection = getattr(self, "_connection", None)
                    if connection is None:
                        raise AttributeError(f"Connection not found in class {self.__name__}")
                    if not isinstance(connection, ConnectionAsync):
                        raise TypeError(
                            f"Connection must be of type ConnectionAsync not {type(connection)} in class {self.__name__} with colour {colour}"
                        )

                    kwargs = __make_kwargs(meta.parameters, *args, **kwargs)
                    result = executor_method(**kwargs, connection=connection)
                    assert isinstance(result, Awaitable)
                    return await result

            else:

                @wraps(metadatum.method)
                def wrapped_method(  # type: ignore
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

                    connection = getattr(self, "_connection", None)
                    if connection is None:
                        raise AttributeError(f"Connection not found in class {self.__name__}")
                    if not isinstance(connection, ConnectionSync):
                        raise TypeError(
                            f"Connection must be of type ConnectionSync not {type(connection)} in class {self.__name__} with colour {colour}"
                        )

                    kwargs = __make_kwargs(meta.parameters, *args, **kwargs)
                    result = executor_method(**kwargs, connection=connection)
                    assert not isinstance(result, Awaitable)
                    return result

            # Add the method to the class
            setattr(cls, metadatum.name, wrapped_method)
        return cls

    return decorator


def __make_kwargs(
    params: MappingProxyType[str, inspect.Parameter], *args: Any, **kwargs: Any
) -> Dict[str, Any]:
    for index, (name, param) in enumerate(params.items()):
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
    return kwargs
