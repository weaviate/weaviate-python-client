import sys
import validators

from .connect import *
from .exceptions import *
from .util import get_uuid_from_weaviate_url, get_domain_from_weaviate_url, is_weaviate_entity_url, is_semantic_type
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS


def add_reference_to_action(self, from_action, from_property_name,
                            to_semantic_type, to_entity, to_weaviate="localhost"):
    """ Allows to link an entity from an action unidirectionally

    :param from_action: The action that should have the reference as part of its properties.
                        Accepts a plane UUID or an URL. E.g.
                        'weaviate://localhost/actions/fc7eb129-f138-457f-b727-1b29db191a67'
                        or
                        'fc7eb129-f138-457f-b727-1b29db191a67'
    :type from_action: str in the form of an UUID, str in form of URL
    :param from_property_name: The name of the property within the action.
    :type from_property_name: str
    :param to_semantic_type: Either things or an actions.
                             Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type to_semantic_type: str
    :param to_entity: The entity that should be referenced.
                      Accepts a plane UUID or an URL. E.g.
                      'weaviate://localhost/actions/fc7eb129-f138-457f-b727-1b29db191a67'
                      or
                      'fc7eb129-f138-457f-b727-1b29db191a67'
    :type to_entity: str in the form of an UUID, str in form of URL
    :param to_weaviate: Specifies the weaviate instance on which the cross referenced action is located.
                        Defaults to 'localhost'.
                        If 'to_action_uuid' specifies an URL then 'to_weviate' must match the given domain
                        or be explicitly set to None.
    :type to_weaviate: str
    :return: None if successful.
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
        TypeError: If the parameters are of the wrong type
        ValueError: If the parameters are of the wrong value
    """
    return self._add_reference_to_entity(SEMANTIC_TYPE_ACTIONS, from_action, from_property_name,
                                         to_semantic_type, to_entity, to_weaviate)


def add_reference_to_thing(self, from_thing, from_property_name,
                           to_semantic_type, to_entity, to_weaviate="localhost"):
    """ Allows to link an entity from a thing unidirectionally.

    :param from_thing: The thing that should have the reference as part of its properties.
                       Accepts a plane UUID or an URL. E.g.
                       'weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67'
                       or
                       'fc7eb129-f138-457f-b727-1b29db191a67'
    :type from_thing: str in the form of an UUID, str in form of URL
    :param from_property_name: The name of the property within the thing.
    :type from_property_name: str
    :param to_semantic_type: Either things or an actions.
                             Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type to_semantic_type: str
    :param to_entity: The UUID of the entity that should be referenced.
                      Accepts a plane UUID or an URL. E.g.
                      'weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67'
                      or
                      'fc7eb129-f138-457f-b727-1b29db191a67'
    :type to_entity: str in the form of an UUID, str in form of URL
    :param to_weaviate: Specifies the weaviate instance on which the cross referenced thing is located.
                        Defaults to 'localhost'.
                        If 'to_thing_uuid' specifies an URL then 'to_weviate' must match the given domain
                        or be explicitly set to None.
    :type to_weaviate: str
    :return: None if successful.
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
        TypeError: If the parameters are of the wrong type
        ValueError: If the parameters are of the wrong value
    """
    return self._add_reference_to_entity(SEMANTIC_TYPE_THINGS, from_thing, from_property_name,
                                         to_semantic_type, to_entity, to_weaviate)


def _add_reference_to_entity(self, from_semantic_type, from_entity, from_property_name, to_semantic_type,
                             to_entity, to_weaviate="localhost"):

    if not isinstance(from_entity, str) or not isinstance(to_entity, str):
        raise TypeError("uuid must be of type str but was: " + str(type(from_entity)))
    if not isinstance(from_property_name, str):
        raise TypeError("from_property_name must be of type str but was: " + str(type(from_property_name)))
    if not is_semantic_type(to_semantic_type):
        raise ValueError("Semantic type must be \"things\" or \"actions\"")

    if is_weaviate_entity_url(from_entity):
        # If url extract uuid
        from_entity = get_uuid_from_weaviate_url(from_entity)
    if not validators.uuid(from_entity):
        raise ValueError(from_entity + " is not a valid uuid")

    if is_weaviate_entity_url(to_entity):

        to_entity_url_weaviate = get_domain_from_weaviate_url(to_entity)
        if to_weaviate is None:
            to_weaviate = to_entity_url_weaviate
        else:
            if to_entity_url_weaviate != to_weaviate:
                raise ValueError("'to_thing_uuid' is defining another weaviate instance, "
                                 "which is inconsistent with 'to_weaviate'."
                                 "'to_weaviate defaults to 'localhost' "
                                 "considder explicitly setting it to the right domain or None.")

        to_entity = get_uuid_from_weaviate_url(to_entity)

    if not validators.uuid(to_entity):
        raise ValueError("to_thing_uuid does not contain a valid uuid")

    if not isinstance(from_property_name, str):
        raise TypeError("'from_property_name' must be type str")
    if from_property_name == "":
        raise ValueError("'from_property_name' can not be empty")

        # Create the beacon
    beacon = {
        "beacon": "weaviate://" + to_weaviate + "/" + to_semantic_type + "/" + to_entity
    }

    path = "/" + from_semantic_type + "/" + from_entity + "/references/" + from_property_name

    try:
        response = self._connection.run_rest(path, REST_METHOD_POST, beacon)
    except ConnectionError as conn_err:
        raise type(conn_err)(
            str(conn_err) + ' Connection error, reference was not added to weaviate.').with_traceback(
            sys.exc_info()[2])

    if response.status_code == 200:
        return
    else:
        raise UnexpectedStatusCodeException("Add property reference to thing", response)


def add_references_in_batch(self, reference_batch_request):
    """ Batch loading references
    Loading batch references is faster by ignoring some validations.
    Loading inconsistent data may ends up in an invalid graph.
    If the consistency of the references is not guaranied use
    add_reference_to_thing to have additional validation instead.

    :param reference_batch_request: contains all the references that should be added in one batch.
    :type reference_batch_request: weaviate.batch.ReferenceBatchRequest
    :return: A list with the status of every reference added.
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """

    if reference_batch_request.get_batch_size() == 0:
        return  # No data in batch

    path = "/batching/references"

    try:
        response = self._connection.run_rest(path, REST_METHOD_POST, reference_batch_request.get_request_body())
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err)
                             + ' Connection error, reference was not added to weaviate.').with_traceback(
            sys.exc_info()[2])

    if response.status_code == 200:
        return response.json()
    else:
        raise UnexpectedStatusCodeException("Add references in batch", response)


# TODO

def delete_reference_from_thing(self, from_thing_uuid, from_property_name,
                                to_semantic_type, to_thing_uuid, to_weaviate="localhost"):
    """ Remove a reference to another thing. Equal to removing one direction of an edge from the graph.

    :param from_thing_uuid: Id of the thing that references another thing.
    :type from_thing_uuid: str in form uuid
    :param from_property_name: The property from which the reference should be deleted.
    :type from_property_name:  str
    :param to_semantic_type: Either things or an actions.
                             Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type to_semantic_type: str
    :param to_thing_uuid: The referenced thing.
    :type to_thing_uuid: str in form uuid
    :param to_weaviate: The other weaviate instance, localhost by default.
    :type to_weaviate: str
    :return: None if successful
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
        TypeError: If parameter has the wrong type.
        ValueError: If uuid is not properly formed.
    """
    return self._delete_reference_from_entity(SEMANTIC_TYPE_THINGS, from_thing_uuid, from_property_name,
                                              to_semantic_type, to_thing_uuid, to_weaviate)


def delete_reference_from_action(self, from_action_uuid, from_property_name,
                                 to_semantic_type, to_action_uuid, to_weaviate="localhost"):
    """ Remove a reference to another action. Equal to removing one direction of an edge from the graph.

    :param from_action_uuid: Id of the action that references another thing.
    :type from_action_uuid: str
    :param from_property_name: The property from which the reference should be deleted.
    :type from_property_name: str
    :param to_semantic_type: Either things or an actions.
                             Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type to_semantic_type: str
    :param to_action_uuid: The referenced action.
    :type to_action_uuid: str
    :param to_weaviate: The other weaviate instance, localhost by default.
    :type to_weaviate: str
    :return: None if successful
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
        TypeError: If parameter has the wrong type.
        ValueError: If uuid is not properly formed.
    """
    return self._delete_reference_from_entity(SEMANTIC_TYPE_ACTIONS, from_action_uuid, from_property_name,
                                              to_semantic_type, to_action_uuid, to_weaviate)


def _delete_reference_from_entity(self, from_semantic_type, from_entity_uuid, from_property_name,
                                  to_semantic_type, to_entity_uuid, to_weaviate="localhost"):

    if not isinstance(from_entity_uuid, str) or not isinstance(to_entity_uuid, str):
        raise TypeError("UUID must be of type str")
    if not validators.uuid(from_entity_uuid) or not validators.uuid(to_entity_uuid):
        raise ValueError("UUID has no proper form")
    if not isinstance(from_property_name, str):
        raise TypeError("Property name must be type str")
    if not isinstance(to_weaviate, str):
        raise TypeError("To weaviate must be type str")
    if not is_semantic_type(to_semantic_type):
        raise ValueError("Semantic type must be \"things\" or \"actions\"")

    beacon = {
        "beacon": "weaviate://" + to_weaviate + "/" + to_semantic_type + "/" + to_entity_uuid
    }

    path = "/" + from_semantic_type + "/" + from_entity_uuid + "/references/" + from_property_name

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

