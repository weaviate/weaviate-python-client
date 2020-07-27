import sys
import validators

from .connect import *
from .exceptions import *
from .util import _get_dict_from_object
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS


def _create(self, entity, class_name, uuid=None, semantic_type=SEMANTIC_TYPE_THINGS, vector_weights=None):
    """ Takes a dict describing the thing and adds it to weaviate

    :param entity: Entity to be added.
    :type entity: dict
    :param class_name: Associated with the entity given.
    :type class_name: str
    :param uuid: Entity will be created under this uuid if it is provided.
                 Otherwise weaviate will generate a uuid for this entity.
    :type uuid: str
    :param semantic_type: Either things or actions.
                          Defaults to things.
                          Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type semantic_type: str
    :param vector_weights: Influence the weight of words on thing creation.
                           Default is None for no influence.
    :type vector_weights: dict
    :return: Returns the UUID of the created thing if successful.
    :raises:
        TypeError: if argument is of wrong type.
        ValueError: if argument contains an invalid value.
        ThingAlreadyExistsException: if an thing with the given uuid already exists within weaviate.
        UnexpectedStatusCodeException: if creating the thing in weavate failed with a different reason,
        more information is given in the exception.
        ConnectionError: if the network connection to weaviate fails.
    :rtype: str
    """

    if not isinstance(entity, dict):
        raise TypeError("Expected" + semantic_type[:-1] + " to be of type dict instead it was: " + str(type(entity)))
    if not isinstance(class_name, str):
        raise TypeError("Expected class_name of type str but was: " + str(type(class_name)))

    weaviate_obj = {
        "class": class_name,
        "schema": entity
    }
    if uuid is not None:
        if not isinstance(uuid, str):
            raise TypeError("Expected uuid to be of type str but was: " + str(type(uuid)))
        if not validators.uuid(uuid):
            raise ValueError("Given uuid does not have a valid form")

        weaviate_obj["id"] = uuid

    if vector_weights is not None:
        if not isinstance(vector_weights, dict):
            raise TypeError("Expected vector_weights to be of type dict but was " + str(type(vector_weights)))

        weaviate_obj["vectorWeights"] = vector_weights

    path = "/" + semantic_type
    try:
        response = self._connection.run_rest(path, REST_METHOD_POST, weaviate_obj)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err) + ' Connection error, object was not added to weaviate.').with_traceback(
            sys.exc_info()[2])

    if response.status_code == 200:
        return str(response.json()["id"])

    else:
        thing_does_already_exist = False
        try:
            if 'already exists' in response.json()['error'][0]['message']:
                thing_does_already_exist = True
        except KeyError:
            pass
        except Exception as e:
            raise type(e)(str(e)
                          + ' Unexpected exception please report this excetpion in an issue.').with_traceback(
                sys.exc_info()[2])

        if thing_does_already_exist:
            raise ThingAlreadyExistsException(str(uuid))

        raise UnexpectedStatusCodeException("Creating thing", response)


def _create_actions_in_batch(self, actions_batch_request):
    """ Crate multiple actions at once in weavaite

    :param actions_batch_request: The batch of actions that should be added.
    :type actions_batch_request: weaviate.ActionsBatchRequest
    :return: A list with the status of every action that was created
    :rtype: list
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """
    return self._create_entity_in_batch(SEMANTIC_TYPE_ACTIONS, actions_batch_request)


def _create_things_in_batch(self, things_batch_request):
    """ Creates multiple things at once in weaviate

    :param things_batch_request: The batch of things that should be added.
    :type things_batch_request: weaviate.ThingsBatchRequest
    :return: A list with the status of every thing that was created.
    :rtype: list
    :raises:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """
    return self._create_entity_in_batch(SEMANTIC_TYPE_THINGS, things_batch_request)


def _create_entity_in_batch(self, semantic_type, batch_request):
    path = "/batching/" + semantic_type

    try:
        response = self._connection.run_rest(path, REST_METHOD_POST, batch_request.get_request_body())
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err) + ' Connection error, batch was not added to weaviate.').with_traceback(
            sys.exc_info()[2])

    if response.status_code == 200:
        return response.json()

    else:
        raise UnexpectedStatusCodeException("Create "+semantic_type+" in batch", response)

def _patch(self, entity, class_name, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
    """ Merges the given thing with the already existing thing in weaviate.
    Overwrites all given fields.

    :param entity: The entity states the fields that should be updated.
                   Fields not stated by entity will not be changed.
                   Fields that are None will not be changed.
    :type entity: dict, url, file
    :param class_name: The name of the class of entity.
    :type class_name: str
    :param uuid: The ID of the entity that should be changed.
    :type uuid: str
    :param semantic_type: Either things or actions.
                          Defaults to things.
                          Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type semantic_type: str
    :return: None if successful
    :raises:
        ConnectionError: If the network connection to weaviate fails.
        UnexpectedStatusCodeException: If weaviate reports a none successful status.
    """
    try:
        entity_dict = _get_dict_from_object(entity)
    except:
        raise  # Keep exception boiling back to user

    if not isinstance(class_name, str):
        raise TypeError("Class must be type str")
    if not isinstance(uuid, str):
        raise TypeError("UUID must be type str")
    if not validators.uuid(uuid):
        raise ValueError("Not a proper UUID")

    payload = {
        "id": uuid,
        "class": class_name,
        "schema": entity_dict
    }

    path = "/"+semantic_type+"/"+uuid

    try:
        response = self._connection.run_rest(path, REST_METHOD_PATCH, payload)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err) + ' Connection error, entity was not patched.').with_traceback(
            sys.exc_info()[2])

    if response.status_code == 204:
        return None  # success
    else:
        raise UnexpectedStatusCodeException("PATCH merge of entity not successful", response)

def _put(self, entity, class_name, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
    """ Replaces an already existing entity with the given entity. Does not keep unset values.

    :param entity: Describes the new values.
                   It may be an URL or path to a json or a python dict describing the new values.
    :type entity: str, dict
    :param class_name: Name of the class of the thing that should be updated.
    :type class_name: str
    :param uuid: Of the entity.
    :type uuid: str
    :param semantic_type: Either things or actions.
                          Defaults to things.
                          Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type semantic_type: str
    :return: None if successful.
    :raises:
        ConnectionError: If the network connection to weaviate fails.
        UnexpectedStatusCodeException: If weaviate reports a none OK status.
    """
    parsed_entity = _get_dict_from_object(entity)

    weaviate_obj = {
        "id": uuid,
        "class": class_name,
        "schema": parsed_entity
    }

    try:
        response = self._connection.run_rest("/" + semantic_type + "/" + uuid, REST_METHOD_PUT, weaviate_obj)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err) + ' Connection error, thing was not updated.').with_traceback(
            sys.exc_info()[2])

    if response.status_code == 200:
        return

    else:
        raise UnexpectedStatusCodeException("Update thing", response)