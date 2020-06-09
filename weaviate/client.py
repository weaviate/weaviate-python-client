import sys
import validators

from .connect import *
from .classify import Classification
from .exceptions import *
from .util import _get_dict_from_object, get_uuid_from_weaviate_url, get_domain_from_weaviate_url, \
    is_weaviate_entity_url
from .client_config import ClientConfig
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS


class Client:
    """ A python native weaviate client
    """

    # Class is splitted into multiple files
    # Other class methods get imported here

    from weaviate._client_schema import create_schema, contains_schema, get_schema, \
        _create_complex_properties, _property_is_primitive, _get_primitive_properties, _create_class_with_primitives
    from weaviate._client_c11y import get_c11y_vector, extend_c11y

    def __init__(self, url, auth_client_secret=None, client_config=None):
        """ New weaviate client

        :param url: To the weaviate instance.
        :type url: str
        :param auth_client_secret: Authentification client secret.
        :type auth_client_secret: weaviate.AuthClientCredentials or weaviate.AuthClientPassword
        :param client_config: Gives additional optimization parameters for the client.
                              Uses default parameters if omitted.
        :type client_config: weaviate.ClientConfig
        """
        if url is None:
            raise TypeError("URL is expected to be string but is None")
        if not isinstance(url, str):
            raise TypeError("URL is expected to be string but is "+str(type(url)))
        if not validators.url(url):
            # IPs ending with 0 are not seen as valid URL
            # Lets check if a valid URL is in place
            ip = url
            if ip.startswith("http://"):
                ip = ip[7:]
            if ip.startswith("https://"):
                ip = ip[8:]
            ip = ip.split(':')[0]
            if not validators.ip_address.ipv4(ip):
                raise ValueError("URL has no propper form: " + url)
        if url.endswith("/"):
            # remove trailing slash
            url = url[:-1]

        if client_config is not None:
            # Check the input
            if (not isinstance(client_config.timeout_config, tuple)) or\
                    (not isinstance(client_config.timeout_config[0], int)) or\
                    (not isinstance(client_config.timeout_config[1], int)):
                raise TypeError("ClientConfig.timeout_config must be tupel of int")
            if len(client_config.timeout_config) > 2 or len(client_config.timeout_config) < 2:
                raise ValueError("ClientConfig.timeout_config must be of length 2")

        else:
            # Create the default config
            client_config = ClientConfig()

        self._connection = connection.Connection(url=url,
                                                 auth_client_secret=auth_client_secret,
                                                 timeout_config=client_config.timeout_config)

        self.classification = Classification(self._connection)

    def create_action(self, action, class_name, uuid=None, vector_weights=None):
        """ Takes a dict describing the action and adds it to weaviate

        :param action: Action to be added.
        :type action: dict
        :param class_name: Associated with the action given.
        :type class_name: str
        :param uuid: Action will be created under this uuid if it is provided.
        :type uuid: str
        :param vector_weights: Influence the weight of words on action creation.
        :type vector_weights: dict
        :return: The UUID of the creaded thing if successful.
        :raises:
            TypeError: if argument is of wrong type.
            ValueError: if argument contains an invalid value.
            ThingAlreadyExistsException: if an thing with the given uuid already exists within weaviate.
            UnexpectedStatusCodeException: if creating the thing in weavate failed with a different reason,
            more information is given in the exception.
            ConnectionError: if the network connection to weaviate fails.
        :rtype: str
        """
        return self._create_entity(SEMANTIC_TYPE_ACTIONS, action, class_name, uuid, vector_weights)

    def create_thing(self, thing, class_name, uuid=None, vector_weights=None):
        """ Takes a dict describing the thing and adds it to weaviate

        :param thing: Thing to be added.
        :type thing: dict
        :param class_name: Associated with the thing given.
        :type class_name: str
        :param uuid: Thing will be created under this uuid if it is provided.
        :type uuid: str
        :param vector_weights: Influence the weight of words on thing creation.
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
        return self._create_entity(SEMANTIC_TYPE_THINGS, thing, class_name, uuid, vector_weights)

    def _create_entity(self, semantic_type, entity, class_name, uuid=None, vector_weights=None):
        """ Implements the generic adding of an object to weaviate.
            See also create_thing and create_action

        :param semantic_type: defined in constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type semantic_type: str
        :param entity:
        :type entity: dict
        :param class_name:
        :type class_name: str
        :param uuid:
        :type uuid: str
        :param vector_weights:
        :type vector_weights: dict
        :return:
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
                raise TypeError("Expected uuid to be of type str but was: "+str(type(uuid)))
            if not validators.uuid(uuid):
                raise ValueError("Given uuid does not have a valid form")

            weaviate_obj["id"] = uuid

        if vector_weights is not None:
            if not isinstance(vector_weights, dict):
                raise TypeError("Expected vector_weights to be of type dict but was "+str(type(vector_weights)))

            weaviate_obj["vectorWeights"] = vector_weights

        path = "/"+semantic_type
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

    def create_actions_in_batch(self, actions_batch_request):
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

    def create_things_in_batch(self, things_batch_request):
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

    def _patch_entity(self, semantic_type, entity, class_name, uuid):
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

    def patch_action(self, action, class_name, uuid):
        """ Merges the given action with the already existing action in weaviate.
        Overwrites all given fields.

        :param action: The action states the fields that should be updated.
                  Fields not stated by action will not be changed.
                  Fields that are None will not be changed (may change in the future to deleted).
        :param class_name: The name of the class of action.
        :type class_name: str
        :param uuid: The ID of the action that should be changed.
        :type uuid: str
        :return: None if successful
        :raises:
            ConnectionError: If the network connection to weaviate fails.
            UnexpectedStatusCodeException: If weaviate reports a none successful status.
        """
        return self._patch_entity(SEMANTIC_TYPE_ACTIONS, action, class_name, uuid)

    def patch_thing(self, thing, class_name, uuid):
        """ Merges the given thing with the already existing thing in weaviate.
        Overwrites all given fields.

        :param thing: The thing states the fields that should be updated.
                      Fields not stated by thing will not be changed.
                      Fields that are None will not be changed (may change in the future to deleted).
        :type thing: dict, url, file
        :param class_name: The name of the class of thing.
        :type class_name: str
        :param uuid: The ID of the thing that should be changed.
        :type uuid: str
        :return: None if successful
        :raises:
            ConnectionError: If the network connection to weaviate fails.
            UnexpectedStatusCodeException: If weaviate reports a none successful status.
        """
        return self._patch_entity(SEMANTIC_TYPE_THINGS, thing, class_name, uuid)

    def add_reference_to_entity(self, from_semantic_type, from_entity_uuid, from_property_name, to_semantic_type, to_entity_uuid, to_weaviate="localhost"):
        if not isinstance(from_entity_uuid, str) or not isinstance(to_entity_uuid, str):
            raise TypeError("uuid must be of type str but was: " + str(type(from_entity_uuid)))
        if not isinstance(from_property_name, str):
            raise TypeError("from_property_name must be of type str but was: " + str(type(from_property_name)))

        if is_weaviate_entity_url(from_entity_uuid):
            # If url extract uuid
            from_entity_uuid = get_uuid_from_weaviate_url(from_entity_uuid)
        if not validators.uuid(from_entity_uuid):
            raise ValueError(from_entity_uuid+" is not a valid uuid")

        if is_weaviate_entity_url(to_entity_uuid):

            to_entity_url_weaviate = get_domain_from_weaviate_url(to_entity_uuid)
            if to_weaviate is None:
                to_weaviate = to_entity_url_weaviate
            else:
                if to_entity_url_weaviate != to_weaviate:
                    raise ValueError("'to_thing_uuid' is defining another weaviate instance, "
                                     "which is inconsistent with 'to_weaviate'."
                                     "'to_weaviate defaults to 'localhost' "
                                     "considder explicitly setting it to the right domain or None.")

            to_entity_uuid = get_uuid_from_weaviate_url(to_entity_uuid)
        if not validators.uuid(to_entity_uuid):
            raise ValueError("to_thing_uuid does not contain a valid uuid")

        if not isinstance(from_property_name, str):
            raise TypeError("'from_property_name' must be type str")
        if from_property_name == "":
            raise ValueError("'from_property_name' can not be empty")

            # Create the beacon
        beacon = {
            "beacon": "weaviate://" + to_weaviate + "/"+ to_semantic_type +"/" + to_entity_uuid
        }

        path = "/"+ from_semantic_type +"/" + from_entity_uuid + "/references/" + from_property_name

        # TODO allow replacement of references
        #:param replace_reference: If true the reference is not appended but replaces an existing reference instead.
        #:type replace_reference: bool
        #
        # method = REST_METHOD_POST
        # if replace_reference:
        #     method = REST_METHOD_PUT

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

    def add_reference_from_action_to_action(self, from_action_uuid, from_property_name, to_action_uuid, to_weaviate="localhost"):
        """ Allows to link two actions unidirectionally

        :param from_action_uuid: The action that should have the reference as part of its properties.
                                 Accepts a plane UUID or an URL. E.g.
                                 'weaviate://localhost/actions/fc7eb129-f138-457f-b727-1b29db191a67'
                                 or
                                 'fc7eb129-f138-457f-b727-1b29db191a67'
        :type from_action_uuid:  str in the form of an UUID
        :param from_property_name: The name of the property within the action.
        :type from_property_name: str
        :param to_action_uuid: The UUID of the action that should be referenced.
                              Accepts a plane UUID or an URL. E.g.
                              'weaviate://localhost/actions/fc7eb129-f138-457f-b727-1b29db191a67'
                              or
                              'fc7eb129-f138-457f-b727-1b29db191a67'
        :type to_action_uuid: str
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
        return self.add_reference_to_entity(SEMANTIC_TYPE_ACTIONS, from_action_uuid, from_property_name,
                                            SEMANTIC_TYPE_ACTIONS, to_action_uuid, to_weaviate)

    def add_reference_from_thing_to_thing(self, from_thing_uuid, from_property_name, to_thing_uuid, to_weaviate="localhost"):
        """ Allows to link two things unidirectionally.

        :param from_thing_uuid: The thing that should have the reference as part of its properties.
                                Accepts a plane UUID or an URL. E.g.
                                'weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67'
                                or
                                'fc7eb129-f138-457f-b727-1b29db191a67'
        :type from_thing_uuid: str in the form of an UUID
        :param from_property_name: The name of the property within the thing.
        :type from_property_name: str
        :param to_thing_uuid: The UUID of the thing that should be referenced.
                              Accepts a plane UUID or an URL. E.g.
                              'weaviate://localhost/things/fc7eb129-f138-457f-b727-1b29db191a67'
                              or
                              'fc7eb129-f138-457f-b727-1b29db191a67'
        :type to_thing_uuid: str in the form of an UUID
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
        return self.add_reference_to_entity(SEMANTIC_TYPE_THINGS, from_thing_uuid, from_property_name,
                                            SEMANTIC_TYPE_THINGS, to_thing_uuid, to_weaviate)

    def put_thing(self, thing, class_name, uuid):
        """ Replaces an already existing thing with the given thing. Does not keep unset values.

        :param thing: Describes the new values.
                      It may be an URL or path to a json or a python dict describing the new values.
        :type thing: str, dict
        :param class_name: Name of the class of the thing that should be updated.
        :type class_name: str
        :param uuid: Of the thing.
        :type uuid: str
        :return: None if successful.
        :raises:
            ConnectionError: If the network connection to weaviate fails.
            UnexpectedStatusCodeException: If weaviate reports a none OK status.
        """

        parsed_thing = _get_dict_from_object(thing)

        weaviate_obj = {
            "id": uuid,
            "class": class_name,
            "schema": parsed_thing
        }

        try:
            response = self._connection.run_rest("/things/" + uuid, REST_METHOD_PUT, weaviate_obj)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, thing was not updated.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return

        else:
            raise UnexpectedStatusCodeException("Update thing", response)

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

    def action_exists(self, action_uuid):
        """

        :param action_uuid: he uuid of the action that may or may not exist within weaviate.
        :type action_uuid: str
        :return: true if action exists
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        return self._entity_exists(SEMANTIC_TYPE_ACTIONS, action_uuid)

    def thing_exists(self, thing_uuid):
        """

        :param thing_uuid: the uuid of the thing that may or may not exist within weaviate.
        :type thing_uuid: str
        :return: true if thing exists.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        return self._entity_exists(SEMANTIC_TYPE_THINGS, thing_uuid)

    def _entity_exists(self, semantic_type, uuid_entity):
        try:
            response = self._get_entity_response(semantic_type, uuid_entity)
        except ConnectionError:
            raise  # Just pass the same error back

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise UnexpectedStatusCodeException("Thing exists", response)

    def get_action(self, action_uuid, meta=False):
        """ Get an action as dict

        :param action_uuid: the identifier of the action that should be retrieved.
        :type action_uuid: str
        :param meta: if True the result includes meta data.
        :type meta: bool
        :return:
            dict in case the action exists.
            None in case the action does not exist.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        return self._get_entity(SEMANTIC_TYPE_ACTIONS, action_uuid, meta)

    def get_thing(self, thing_uuid, meta=False):
        """ Gets a thing as dict.

        :param thing_uuid: the identifier of the thing that should be retrieved.
        :type thing_uuid: str
        :param meta: if True the result includes meta data.
        :type meta: bool
        :return:
            dict in case the thing exists.
            None in case the thing does not exist.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        return self._get_entity(SEMANTIC_TYPE_THINGS, thing_uuid, meta)

    def _get_entity(self, semantic_type, entity_uuid, meta):
        try:
            response = self._get_entity_response(semantic_type, entity_uuid, meta)
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




    def is_reachable(self):
        """ Ping weaviate

        :return: True if weaviate could be reached False otherwise.
        """
        try:

            response = self._connection.run_rest("/.well-known/ready", REST_METHOD_GET)
            if response.status_code == 200:
                return True
            return False
        except ConnectionError:
            return False


    def delete_action(self, action_uuid):
        """

        :param action_uuid: ID of the action that should be removed from the graph.
        :type action_uuid: str
        :return: None if successful
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
            TypeError: If parameter has the wrong type.
            ValueError: If uuid is not properly formed.
        """
        return self._delete_entity(SEMANTIC_TYPE_ACTIONS, action_uuid)

    def delete_thing(self, thing_uuid):
        """

        :param thing_uuid: ID of the thing that should be removed from the graph.
        :type thing_uuid: str
        :return: None if successful
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
            TypeError: If parameter has the wrong type.
            ValueError: If uuid is not properly formed.
        """
        return self._delete_entity(SEMANTIC_TYPE_THINGS, thing_uuid)

    def _delete_entity(self, semantic_type, entity_uuid):
        if not isinstance(entity_uuid, str):
            raise TypeError("UUID must be type str")
        if not validators.uuid(entity_uuid):
            raise ValueError("UUID does not have proper form")

        try:
            response = self._connection.run_rest("/" + semantic_type + "/" + entity_uuid, REST_METHOD_DELETE)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, entity could not be deleted.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 204:
            return  # Successfully deleted
        else:
            raise UnexpectedStatusCodeException("Delete entity", response)

    def delete_reference_from_thing_to_thing(self, from_thing_uuid, from_property_name, to_thing_uuid, to_weaviate="localhost"):
        """ Remove a reference to another thing. Equal to removing one direction of an edge from the graph.

        :param from_thing_uuid: Id of the thing that references another thing.
        :type from_thing_uuid: str in form uuid
        :param from_property_name: The property from which the reference should be deleted.
        :type from_property_name:  str
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
        return self.delete_reference_from_entity(SEMANTIC_TYPE_THINGS, from_thing_uuid, from_property_name,
                                                 SEMANTIC_TYPE_THINGS, to_thing_uuid, to_weaviate)

    def delete_reference_from_action_to_action(self, from_action_uuid, from_property_name, to_action_uuid, to_weaviate="localhost"):
        """ Remove a reference to another action. Equal to removing one direction of an edge from the graph.

        :param from_action_uuid: Id of the action that references another thing.
        :type from_action_uuid: str
        :param from_property_name: The property from which the reference should be deleted.
        :type from_property_name: str
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
        return self.delete_reference_from_entity(SEMANTIC_TYPE_ACTIONS, from_action_uuid, from_property_name,
                                                 SEMANTIC_TYPE_ACTIONS, to_action_uuid, to_weaviate)

    def delete_reference_from_entity(self, from_semantic_type, from_entity_uuid, from_property_name,
                                     to_smeantic_type, to_entity_uuid, to_weaviate="localhost"):

        if not isinstance(from_entity_uuid, str) or not isinstance(to_entity_uuid, str):
            raise TypeError("UUID must be of type str")
        if not validators.uuid(from_entity_uuid) or not validators.uuid(to_entity_uuid):
            raise ValueError("UUID has no proper form")
        if not isinstance(from_property_name, str):
            raise TypeError("Property name must be type str")
        if not isinstance(to_weaviate, str):
            raise TypeError("To weaviate must be type str")

        beacon = {
            "beacon": "weaviate://" + to_weaviate + "/" + to_smeantic_type + "/" + to_entity_uuid
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

    def query(self, gql_query):
        """ Allows to send simple graph QL string queries.
            To create more complex GQL queries please use a GQL python client.
            Be cautious of injection risks when generating query strings.

        :param gql_query: A GQL query in form of a string
        :type gql_query: str
        :return: Data response of the query
        :raises:
            TypeError: If parameter has the wrong type.
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        if not isinstance(gql_query, str):
            raise TypeError("Query is expected to be a string")

        json_query = {"query": gql_query}

        try:
            response = self._connection.run_rest("/graphql", REST_METHOD_POST, json_query)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, query not executed.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return response.json() # Successfully queried
        else:
            raise UnexpectedStatusCodeException("GQL query", response)

