"""Shared helpers for the in-Pyodide test modules (pytest is not available here)."""

import contextlib
import sys
from typing import Any, Optional


class _Caught:
    value: Any


@contextlib.contextmanager
def raises(exc_type, contains: Optional[str] = None):
    """``pytest.raises`` stand-in; ``contains`` is a plain substring, not a regex."""
    caught = _Caught()
    try:
        yield caught
    except exc_type as e:
        caught.value = e
        if contains is not None and contains not in str(e):
            raise AssertionError(f"{e!r} does not contain {contains!r}") from e
    else:
        raise AssertionError(f"expected {exc_type.__name__} to be raised")


@contextlib.contextmanager
def patched(obj, name: str, value):
    """``monkeypatch.setattr`` stand-in with restore-on-exit."""
    sentinel = object()
    old = getattr(obj, name, sentinel)
    setattr(obj, name, value)
    try:
        yield
    finally:
        if old is sentinel:
            delattr(obj, name)
        else:
            setattr(obj, name, old)


@contextlib.contextmanager
def sys_module(name: str, module):
    """Set ``sys.modules[name]`` (``None`` makes ``import name`` raise) and restore."""
    present = name in sys.modules
    old = sys.modules.get(name)
    sys.modules[name] = module
    try:
        yield
    finally:
        if present:
            sys.modules[name] = old  # type: ignore[assignment]
        else:
            del sys.modules[name]
