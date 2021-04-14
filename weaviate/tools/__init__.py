"""
Module used to automaticaly submit batches to weaviate.
"""

__all__ = ['Batcher', 'WCS', 'generate_uuid']

from typing import Any
import uuid
from .batcher import Batcher
from .wcs import WCS


def generate_uuid(identifier: Any, namespace: Any = "") -> str:
    """
    Generate an UUID, may be used to consistently generate the same UUID for a specific identifier
    and namespace.

    Parameters
    ----------
    identifier : Any
        The identifier/object that should be used as basis for the UUID.
    namespace : Any, optional
        Allows to namespace the identifier, by default ""

    Returns
    -------
    str
        The UUID as a string.
    """

    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(namespace) + str(identifier)))
