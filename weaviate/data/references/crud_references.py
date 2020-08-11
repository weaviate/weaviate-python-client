import sys
import validators

from weaviate.connect import *
from weaviate.exceptions import *
from weaviate.util import get_uuid_from_weaviate_url, get_domain_from_weaviate_url, is_weaviate_entity_url, is_semantic_type
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_THINGS


class Reference:

    def __init__(self, connection):
        self._connection = connection

    def replace(self, from_uuid, from_property_name, to_uuids,
            from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS,
            to_weaviate="localhost"):
        pass

    def add(self, from_uuid, from_property_name, to_uuid,
                  from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS):
        """ Allows to link an entity from a thing unidirectionally.

        :param from_uuid: The entity that should have the reference as part of its properties.
                           Accepts a plane UUID or an URL. E.g.
                           'http://localhost:8080/v1/things/fc7eb129-f138-457f-b727-1b29db191a67'
                           or
                           'fc7eb129-f138-457f-b727-1b29db191a67'
                           By default the entity is a thing please specify from_semantic_type
                           if you want to reference from an action.
        :type from_uuid: str in the form of an UUID, str in form of URL
        :param from_property_name: The name of the property within the entity.
        :type from_property_name: str
        :param to_uuid: The UUID of the entity that should be referenced.
                          Accepts a plane UUID or an URL. E.g.
                          'weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67'
                          or
                          'fc7eb129-f138-457f-b727-1b29db191a67'
        :type to_uuid: str in the form of an UUID, str in form of URL
        :param from_semantic_type: Either things or actions.
                                   Defaults to things.
                                   Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type from_semantic_type: str
        :param to_semantic_type: Either things or actions.
                                 Defaults to things.
                                 Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type to_semantic_type: str
        :return: None if successful.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
            TypeError: If the parameters are of the wrong type
            ValueError: If the parameters are of the wrong value
        """
        from_uuid = self._validate_and_get_from_uuid(from_uuid)
        self._validate_property_and_semantic_types(from_property_name, from_semantic_type, to_semantic_type)
        to_uuid, to_weaviate = self._validate_and_get_to_uuid_and_to_weaviate(to_uuid)

        if not isinstance(from_property_name, str):
            raise TypeError("'from_property_name' must be type str")
        if from_property_name == "":
            raise ValueError("'from_property_name' can not be empty")

            # Create the beacon
        beacon = {
            "beacon": "weaviate://" + to_weaviate + "/" + to_semantic_type + "/" + to_uuid
        }

        path = "/" + from_semantic_type + "/" + from_uuid + "/references/" + from_property_name

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

    def _validate_and_get_from_uuid(self, from_uuid):
        if not isinstance(from_uuid, str):
            raise TypeError("uuid must be of type str but was: " + str(type(from_uuid)))

        if is_weaviate_entity_url(from_uuid):
            # If url extract uuid
            from_uuid = get_uuid_from_weaviate_url(from_uuid)
        if not validators.uuid(from_uuid):
            raise ValueError(from_uuid + " is not a valid uuid")
        return from_uuid

    def _validate_and_get_to_uuid_and_to_weaviate(self, to_uuid, to_weaviate):
        if not isinstance(to_uuid, str):
            raise TypeError("uuid must be of type str but was: " + str(type(to_uuid)))

        if is_weaviate_entity_url(to_uuid):

            to_entity_url_weaviate = get_domain_from_weaviate_url(to_uuid)
            if to_weaviate is None:
                to_weaviate = to_entity_url_weaviate
            else:
                if to_entity_url_weaviate != to_weaviate:
                    raise ValueError("'to_thing_uuid' is defining another weaviate instance, "
                                     "which is inconsistent with 'to_weaviate'."
                                     "'to_weaviate defaults to 'localhost' "
                                     "considder explicitly setting it to the right domain or None.")

            to_uuid = get_uuid_from_weaviate_url(to_uuid)

        if not validators.uuid(to_uuid):
            raise ValueError("to_thing_uuid does not contain a valid uuid")

        return to_uuid, to_weaviate

    def _validate_property_and_semantic_types(self, from_property_name, from_semantic_type, to_semantic_type):
        if not isinstance(from_property_name, str):
            raise TypeError("from_property_name must be of type str but was: " + str(type(from_property_name)))
        if not is_semantic_type(to_semantic_type) or not is_semantic_type(from_semantic_type):
            raise ValueError("Semantic type must be \"things\" or \"actions\"")

    def _create_reference(self, from_uuid, from_property_name, to_uuid,
            from_semantic_type, to_semantic_type, to_weaviate, rest_method):
        pass