import asyncio
from functools import wraps
from typing import TypeVar

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
