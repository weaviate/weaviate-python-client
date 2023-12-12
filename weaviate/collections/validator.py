from functools import partial
from inspect import signature
from typing import (
    Any,
    Callable,
    Generic,
    ParamSpec,
    Set,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

P = ParamSpec("P")
R = TypeVar("R")


class _Validator(Generic[P, R]):
    def __init__(self, func: Callable[P, R], include_params: Set[str]):
        """Use a class decorator so that get_type_hints is cached for each function invocation."""
        self.func = func
        self.type_hints = get_type_hints(func)
        self.include = include_params
        self.all = include_params == {"all"}

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Decorate the function by reading the type hints in the signature and checking the types of the arguments passed to the function."""
        bound_args = signature(self.func).bind(*args, **kwargs)
        bound_args.apply_defaults()
        for name, value in bound_args.arguments.items():
            if not self.all and name not in self.include:
                continue
            if name in self.type_hints:
                expected_type = self.type_hints[name]
                if get_origin(expected_type) == list:
                    if not isinstance(value, list):
                        raise TypeError(
                            f"Argument '{name}' must be {expected_type}, but got {type(value)}"
                        )
                    expected_inner_type = get_args(expected_type)[0]
                    for item in value:
                        if not isinstance(item, expected_inner_type):
                            raise TypeError(
                                f"List element of argument '{name}' must be {expected_inner_type}, but got {type(item)}"
                            )
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Argument '{name}' must be {expected_type}, but got {type(value)}"
                    )
        return self.func(*args, **kwargs)

    def __get__(self, instance: Any, owner: Any) -> Callable[P, R]:
        """Ensure that the decorator can be used on instance methods.

        https://stackoverflow.com/questions/69288996/why-is-self-not-in-args-when-using-a-class-as-a-decorator

        https://stackoverflow.com/questions/30104047/how-can-i-decorate-an-instance-method-with-a-decorator-class/30105234#30105234
        """
        return partial(self.__call__, instance)


def validate(*include_params: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Validate that the arguments passed to the function are of the correct type.

    Only works for simple type arguments and not generics so functions with generic arguments should be handled on a case-by-case basis.
    To use this decorator in a function with more complex types that aren't handled then pass the names of the arguments that you want validated,
    and the rest will be ignored.

    Example:
        >>> @validate("all")
        ... def foo(bar: str, baz: int) -> None:
        ...     print(bar, baz)
        >>> foo("hello", 1)
        hello 1
        >>> foo(1, "hello")
        TypeError: Argument 'bar' must be <class 'str'>, but got <class 'int'>
        >>> foo("hello", 1, "extra")
        TypeError: too many positional arguments
        >>> foo("hello", 1, extra="extra")
        TypeError: got an unexpected keyword argument 'extra'
        >>> @validate("baz")
        ... def foo(bar: str, baz: int) -> None:
        ...     print(bar, baz)
        >>> foo(1, "hello")
        1 hello
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        return _Validator(func, set(include_params))

    return decorator
