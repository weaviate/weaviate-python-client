"""Suppress the ``authlib.jose`` deprecation warning emitted by authlib >=1.7.0.

authlib registers ``simplefilter("always", AuthlibDeprecationWarning)`` at import time,
so we must import the category first to insert our filter in front of it.

Remove this module (and its import in ``weaviate/__init__.py``) once the ``authlib``
pin in ``setup.cfg`` moves to ``>=2.0.0``.
"""

import warnings

from authlib.deprecate import AuthlibDeprecationWarning

warnings.filterwarnings("ignore", category=AuthlibDeprecationWarning)
