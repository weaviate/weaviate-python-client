import sys
import validators

from .connect import *
from .exceptions import *
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_THINGS


def exists(self, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
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


def get(self, uuid, meta=False, semantic_type=SEMANTIC_TYPE_THINGS):
    """ Gets a thing as dict.

    :param uuid: the identifier of the thing that should be retrieved.
    :type uuid: str
    :param meta: if True the result includes meta data.
    :type meta: bool
    :param semantic_type: defaults to things allows also actions see SEMANTIC_TYPE_ACTIONS.
    :type semantic_type: str
    :return:
        dict in case the thing exists.
        None in case the thing does not exist.
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """

    try:
        response = self._get_entity_response(semantic_type, uuid, meta)
    except ConnectionError:
        raise

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        raise UnexpectedStatusCodeException("Get entity", response)


def _get_entity_response(self, semantic_type, entity_uuid, meta=False):
    """ Retrieves an entity from weaviate.

    :param semantic_type: can be found as constants e.g. SEMANTIC_TYPE_THINGS.
    :type semantic_type: str
    :param entity_uuid: the identifier of the entity that should be retrieved.
    :type entity_uuid: str
    :param meta: if True the result includes meta data.
    :type meta: bool
    :return: response object.
    :raises:
        ConnectionError: if the network connection to weaviate fails.
    """
    params = {}
    if meta:
        params['meta'] = True
    if not isinstance(entity_uuid, str):
        entity_uuid = str(entity_uuid)
    try:
        response = self._connection.run_rest("/" + semantic_type + "/" + entity_uuid, REST_METHOD_GET, params=params)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err) + ' Connection error not sure if entity exists').with_traceback(
            sys.exc_info()[2])
    else:
        return response


def delete(self, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
    """

    :param uuid: ID of the thing that should be removed from the graph.
    :type uuid: str
    :param semantic_type: defaults to things allows also actions see SEMANTIC_TYPE_ACTIONS.
    :type semantic_type: str
    :return: None if successful
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
        TypeError: If parameter has the wrong type.
        ValueError: If uuid is not properly formed.
    """
    if not isinstance(uuid, str):
        raise TypeError("UUID must be type str")
    if not validators.uuid(uuid):
        raise ValueError("UUID does not have proper form")

    try:
        response = self._connection.run_rest("/" + semantic_type + "/" + uuid, REST_METHOD_DELETE)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err)
                             + ' Connection error, entity could not be deleted.'
                             ).with_traceback(
            sys.exc_info()[2])

    if response.status_code == 204:
        return  # Successfully deleted
    else:
        raise UnexpectedStatusCodeException("Delete entity", response)
