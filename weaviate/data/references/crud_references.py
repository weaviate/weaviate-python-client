import sys

from weaviate.connect import *
from weaviate.exceptions import *
from weaviate.util import is_semantic_type, ParsedUUID
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_THINGS


class Reference:

    def __init__(self, connection):
        self._connection = connection

    def delete(self, from_uuid, from_property_name, to_uuid,
               from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS):
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
            :return: None if successful
            :raises:
                ConnectionError: if the network connection to weaviate fails.
                UnexpectedStatusCodeException: if weaviate reports a none OK status.
                TypeError: If parameter has the wrong type.
                ValueError: If uuid is not properly formed.
            """

        from_uuid_parsed = _validate_uuid_get_parsed(from_uuid, from_semantic_type)
        to_uuid_parsed = _validate_uuid_get_parsed(to_uuid, to_semantic_type)
        _validate_property_name(from_property_name)
        _validate_semantic_types(from_semantic_type, to_semantic_type)

        beacon = _get_beacon(to_semantic_type, to_uuid_parsed.uuid)
        path = f"/{from_semantic_type}/{from_uuid_parsed.uuid}/references/{from_property_name}"

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

    def replace(self, from_uuid, from_property_name, to_uuids,
                from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS):
        """ Allows to replace all references in that property with a new set of references

        :param from_uuid: The object that should have the reference as part of its properties.
                           Accepts a plane UUID or an URL. E.g.
                           'http://localhost:8080/v1/things/fc7eb129-f138-457f-b727-1b29db191a67'
                           or
                           'fc7eb129-f138-457f-b727-1b29db191a67'
                           By default the object is a thing please specify from_semantic_type
                           if you want to reference from an action.
        :type from_uuid: str in the form of an UUID, str in form of URL
        :param from_property_name: The name of the property within the object.
        :type from_property_name: str
        :param to_uuids: The UUIDs of the objects that should be referenced.
                          Accepts a plane UUID or an URL. E.g.
                          ['http://localhost:8080/v1/things/fc7eb129-f138-457f-b727-1b29db191a67', ...]
                          or
                          ['fc7eb129-f138-457f-b727-1b29db191a67', ...]
        :type to_uuids: list of str with str in the form of an UUID, str in form of URL
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

        from_uuid_parsed = _validate_uuid_get_parsed(from_uuid, from_semantic_type)

        if not isinstance(to_uuids, list):
            to_uuids = [to_uuids]
        to_uuids_parsed = []
        for to_uuid in to_uuids:
            to_uuids_parsed.append(_validate_uuid_get_parsed(to_uuid, to_semantic_type))

        _validate_property_name(from_property_name)
        _validate_semantic_types(from_semantic_type, to_semantic_type)

        beacons = []
        for to_uuid_parsed in to_uuids_parsed:
            beacons.append(_get_beacon(to_semantic_type, to_uuid_parsed.uuid))

        path = f"/{from_semantic_type}/{from_uuid_parsed.uuid}/references/{from_property_name}"

        try:
            response = self._connection.run_rest(path, REST_METHOD_PUT, beacons)
        except ConnectionError as conn_err:
            raise type(conn_err)(
                str(conn_err) + ' Connection error, reference was not replaced in weaviate.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return
        else:
            raise UnexpectedStatusCodeException("Replace property reference to object", response)

    def add(self, from_uuid, from_property_name, to_uuid,
            from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS):
        """ Allows to link an object from a thing unidirectionally.

        :param from_uuid: The object that should have the reference as part of its properties.
                           Accepts a plane UUID or an URL. E.g.
                           'http://localhost:8080/v1/things/fc7eb129-f138-457f-b727-1b29db191a67'
                           or
                           'fc7eb129-f138-457f-b727-1b29db191a67'
                           By default the object is a thing please specify from_semantic_type
                           if you want to reference from an action.
        :type from_uuid: str in the form of an UUID, str in form of URL
        :param from_property_name: The name of the property within the object.
        :type from_property_name: str
        :param to_uuid: The UUID of the object that should be referenced.
                          Accepts a plane UUID or an URL. E.g.
                          'http://localhost:8080/v1/things/fc7eb129-f138-457f-b727-1b29db191a67'
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

        from_uuid_parsed = _validate_uuid_get_parsed(from_uuid, from_semantic_type)
        to_uuid_parsed = _validate_uuid_get_parsed(to_uuid, to_semantic_type)
        _validate_property_name(from_property_name)
        _validate_semantic_types(from_semantic_type, to_semantic_type)

        # Create the beacon
        beacon = _get_beacon(to_semantic_type, to_uuid_parsed.uuid)

        path = f"/{from_semantic_type}/{from_uuid_parsed.uuid}/references/{from_property_name}"

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


def _get_beacon(to_semantic_type, to_uuid):
    return {
        "beacon": f"weaviate://localhost/{to_semantic_type}/{to_uuid}"
    }


def _validate_semantic_types(from_semantic_type, to_semantic_type):
    if not is_semantic_type(to_semantic_type) or not is_semantic_type(from_semantic_type):
        raise ValueError("Semantic type must be \"things\" or \"actions\"")


def _validate_property_name(from_property_name):
    if not isinstance(from_property_name, str):
        raise TypeError("from_property_name must be of type str but was: " + str(type(from_property_name)))


def _validate_uuid_get_parsed(uuid, compare_semantic_type):
    """

    :param uuid:
    :param compare_semantic_type: the semantic type that must fit the specified in the uuid (if any)
    :return:
    :rtype: ParsedUUID
    """
    uuid_parsed = ParsedUUID(uuid)
    if not uuid_parsed.is_valid:
        raise ValueError("not valid uuid or uuid can not be extracted from value")

    if uuid_parsed.semantic_type == None:
        return uuid_parsed

    if not uuid_parsed.semantic_type == compare_semantic_type:
        raise ValueError("semantic_type and the in uuid defined semantic type are conflicting")

    return uuid_parsed