import sys
import validators

from .connect import *
from .exceptions import *
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_THINGS


def _exists(self, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
    """

    :param uuid: the uuid of the thing that may or may not exist within weaviate.
    :type uuid: str
    :param semantic_type: defaults to things allows also actions see SEMANTIC_TYPE_ACTIONS.
    :type semantic_type: str
    :return: true if thing exists.
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """
    try:
        response = self._get_entity_response(semantic_type, uuid)
    except ConnectionError:
        raise  # Just pass the same error back

    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        raise UnexpectedStatusCodeException("Thing exists", response)


def _delete(self, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
