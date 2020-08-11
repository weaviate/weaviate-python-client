import sys
import validators

from .connect import *
from .exceptions import *
from .util import get_uuid_from_weaviate_url, get_domain_from_weaviate_url, is_weaviate_entity_url, is_semantic_type
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_THINGS


def _delete_reference(self, from_uuid, from_property_name, to_uuid,
                     from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS,
                     to_weaviate="localhost"):
    """ Remove a reference to another thing. Equal to removing one direction of an edge from the graph.

    :param from_uuid: Id of the thing that references another thing.
    :type from_uuid: str in form uuid
    :param from_property_name: The property from which the reference should be deleted.
    :type from_property_name:  str
    :param from_semantic_type: Either things or actions.
                               Defaults to things.
                               Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type from_semantic_type: str
    :param to_semantic_type: Either things or actions.
                             Defaults to things.
                             Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type to_semantic_type: str
    :param to_uuid: The referenced thing.
    :type to_uuid: str in form uuid
    :param to_weaviate: The other weaviate instance, localhost by default.
    :type to_weaviate: str
    :return: None if successful
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
        TypeError: If parameter has the wrong type.
        ValueError: If uuid is not properly formed.
    """

    if not isinstance(from_uuid, str) or not isinstance(to_uuid, str):
        raise TypeError("UUID must be of type str")
    if not validators.uuid(from_uuid) or not validators.uuid(to_uuid):
        raise ValueError("UUID has no proper form")
    if not isinstance(from_property_name, str):
        raise TypeError("Property name must be type str")
    if not isinstance(to_weaviate, str):
        raise TypeError("To weaviate must be type str")
    if not is_semantic_type(to_semantic_type):
        raise ValueError("Semantic type must be \"things\" or \"actions\"")

    beacon = {
        "beacon": "weaviate://" + to_weaviate + "/" + to_semantic_type + "/" + to_uuid
    }

    path = "/" + from_semantic_type + "/" + from_uuid + "/references/" + from_property_name

    try:
        response = self._connection.run_rest(path, REST_METHOD_DELETE, beacon)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err)
                             + ' Connection error, reference could not be deleted.'
                             ).with_traceback(
            sys.exc_info()[2])

    if response.status_code == 204:
        return  # Successfully deleted
    else:
        raise UnexpectedStatusCodeException("Delete reference", response)
