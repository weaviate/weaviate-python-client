import sys
import validators

from .connect import *
from .classify import Classification
from .exceptions import *
from .util import _get_dict_from_object, get_uuid_from_weaviate_url, get_domain_from_weaviate_url, \
    is_weaviate_thing_url, _is_sub_schema
from .client_config import ClientConfig
from .validate_schema import validate_schema
from requests.exceptions import ConnectionError

SCHEMA_CLASS_TYPE_THINGS = "things"
SCHEMA_CLASS_TYPE_ACTIONS = "actions"

_PRIMITIVE_WEAVIATE_TYPES = ["string", "int", "boolean", "number", "date", "text", "geoCoordinates", "CrossRef"]


class Client:
    """ A python native weaviate client
    """

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
        """

        if not isinstance(thing, dict):
            raise TypeError("Expected thing to be of type dict instead it was: "+str(type(thing)))
        if not isinstance(class_name, str):
            raise TypeError("Expected class_name of type str but was: "+str(type(class_name)))

        weaviate_obj = {
            "class": class_name,
            "schema": thing
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

        try:
            response = self._connection.run_rest("/things", REST_METHOD_POST, weaviate_obj)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, thing was not added to weaviate.').with_traceback(
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

    def create_things_in_batch(self, things_batch_request):
        """ Creates multiple things at once in weaviate

        :param things_batch_request: The batch of things that should be added.
        :type things_batch_request: ThingsBatchRequest
        :return: A list with the status of every thing that was created.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        path = "/batching/things"

        try:
            response = self._connection.run_rest(path, REST_METHOD_POST, things_batch_request.get_request_body())
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, batch was not added to weaviate.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()

        else:
            raise UnexpectedStatusCodeException("Create thing in batch", response)

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

        try:
            thing_object = _get_dict_from_object(thing)
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
            "schema": thing
        }

        try:
            response = self._connection.run_rest("/things/" + uuid, REST_METHOD_PATCH, payload)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, thing was not patched.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 204:
            return None  # success
        else:
            raise UnexpectedStatusCodeException("PATCH merge of thing not successful", response)



    def add_reference_to_thing(self, from_thing_uuid, from_property_name, to_thing_uuid, to_weaviate="localhost"):
        """ Allows to link two objects unidirectionally.

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

        if not isinstance(from_thing_uuid, str):
            raise TypeError("from_thing_uuid must be of type str but was: " + str(type(from_thing_uuid)))
        if not isinstance(from_property_name, str):
            raise TypeError("from_property_name must be of type str but was: " + str(type(from_property_name)))
        if not isinstance(to_thing_uuid, str):
            raise TypeError("to_thing_uuid must be of type str but was: " + str(type(to_thing_uuid)))

        if is_weaviate_thing_url(from_thing_uuid):
            # If url extract uuid
            from_thing_uuid = get_uuid_from_weaviate_url(from_thing_uuid)
        if not validators.uuid(from_thing_uuid):
            raise ValueError("from_thing_uuid does not contain a valid uuid")

        if is_weaviate_thing_url(to_thing_uuid):

            to_thing_url_weavaite = get_domain_from_weaviate_url(to_thing_uuid)
            if to_weaviate is None:
                to_weaviate = to_thing_url_weavaite
            else:
                if to_thing_url_weavaite != to_weaviate:
                    raise ValueError("'to_thing_uuid' is defining another weaviate instance, "
                                     "which is inconsistent with 'to_weaviate'."
                                     "'to_weaviate defaults to 'localhost' "
                                     "considder explicitly setting it to the right domain or None.")

            to_thing_uuid = get_uuid_from_weaviate_url(to_thing_uuid)
        if not validators.uuid(to_thing_uuid):
            raise ValueError("to_thing_uuid does not contain a valid uuid")

        if not isinstance(from_property_name, str):
            raise TypeError("'from_property_name' must be type str")
        if from_property_name == "":
            raise ValueError("'from_property_name' can not be empty")

        # Create the beacon
        beacon = {
            "beacon": "weaviate://"+to_weaviate+"/things/"+to_thing_uuid
        }

        path = "/things/" + from_thing_uuid + "/references/" + from_property_name

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

    def thing_exists(self, uuid_thing):
        """

        :param uuid_thing: the uuid of the thing that may or may not exist within weaviate.
        :type uuid_thing: str
        :return: true if thing exists.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        try:
            response = self._get_thing_response(uuid_thing)
        except ConnectionError:
            raise  # Just pass the same error back

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise UnexpectedStatusCodeException("Thing exists", response)

    def get_thing(self, uuid_thing, meta=False):
        """ Gets a thing as dict.

        :param uuid_thing: the identifier of the thing that should be retrieved.
        :type uuid_thing: str
        :param meta: if True the result includes meta data.
        :type meta: bool
        :return:
            dict in case the thing exists.
            None in case the thing does not exist.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        try:
            response = self._get_thing_response(uuid_thing, meta)
        except ConnectionError:
            raise

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            raise UnexpectedStatusCodeException("Get thing", response)

    def _get_thing_response(self, uuid_thing, meta=False):
        """ Retrieves a thing from weaviate.

        :param uuid_thing: the identifier of the thing that should be retrieved.
        :type uuid_thing: str
        :param meta: if True the result includes meta data.
        :type meta: bool
        :return: response object.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
        """
        params = {}
        if meta:
            params['meta'] = True
        if not isinstance(uuid_thing, str):
            uuid_thing = str(uuid_thing)
        try:
            response = self._connection.run_rest("/things/" + uuid_thing, REST_METHOD_GET, params=params)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error not sure if thing exists').with_traceback(
                sys.exc_info()[2])
        else:
            return response

    def get_c11y_vector(self, word):
        """ Retrieves the vector representation of the given word.

        :param word: for which the vector should be retrieved. May be CamelCase for word combinations.
        :type word: str
        :return: the vector or vectors of the given word.
            The vector might be empty if the c11y does not contain it.
        :raises:
            AttributeError:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        path = "/c11y/words/" + word
        try:
            response = self._connection.run_rest(path, REST_METHOD_GET)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, c11y vector was not retrieved.').with_traceback(
                sys.exc_info()[2])
        except AttributeError:
            raise
        except Exception as e:
            raise type(e)(
                str(e) + ' Unexpected exception please report this excetpion in an issue.').with_traceback(
                sys.exc_info()[2])
        else:
            if response.status_code == 200:
                return response.json()
            else:
                raise UnexpectedStatusCodeException("C11y vector", response)

    def create_schema(self, schema):
        """ Create the schema at the weaviate instance.

        :param schema: can either be the path to a json file, a url of a json file or a python native dict.
        :type schema: str, dict
        :return: None if successful.
        :raises:
            TypeError: if the schema is neither a string nor a dict.
            ValueError: if schema can not be converted into a weaviate schema.
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
            SchemaValidationException: if the schema could not be validated against the standard format.
        """
        try:
            loaded_schema = _get_dict_from_object(schema)
        except ConnectionError:
            raise
        except UnexpectedStatusCodeException:
            raise

        # validate the schema before loading
        validate_schema(loaded_schema)

        if SCHEMA_CLASS_TYPE_THINGS in loaded_schema:
            self._create_class_with_primitives(SCHEMA_CLASS_TYPE_THINGS,
                                               loaded_schema[SCHEMA_CLASS_TYPE_THINGS]["classes"])
        if SCHEMA_CLASS_TYPE_ACTIONS in loaded_schema:
            self._create_class_with_primitives(SCHEMA_CLASS_TYPE_ACTIONS,
                                               loaded_schema[SCHEMA_CLASS_TYPE_ACTIONS]["classes"])
        if SCHEMA_CLASS_TYPE_THINGS in loaded_schema:
            self._create_complex_properties(SCHEMA_CLASS_TYPE_THINGS,
                                            loaded_schema[SCHEMA_CLASS_TYPE_THINGS]["classes"])
        if SCHEMA_CLASS_TYPE_ACTIONS in loaded_schema:
            self._create_complex_properties(SCHEMA_CLASS_TYPE_ACTIONS,
                                            loaded_schema[SCHEMA_CLASS_TYPE_ACTIONS]["classes"])

    def _create_class_with_primitives(self, schema_class_type, schema_classes_list):
        """ Create all the classes in the list and primitive properties.
        This function does not create references,
        to avoid references to classes that do not yet exist.

        :param schema_class_type: can be found as constants e.g. SCHEMA_CLASS_TYPE_THINGS.
        :type schema_class_type: SCHEMA_CLASS_TYPE_THINGS or SCHEMA_CLASS_TYPE_ACTIONS
        :param schema_classes_list: classes as they are found in a schema json description.
        :type schema_classes_list: list
        :return: None if successful.
        :raises
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        for weaviate_class in schema_classes_list:

            # Create the class
            schema_class = {
                "class": weaviate_class['class'],
                "description": weaviate_class['description'],
                "properties": [],
                "keywords": []
            }

            if "vectorizeClassName" in weaviate_class:
                schema_class["vectorizeClassName"] = weaviate_class["vectorizeClassName"]

            if "properties" in weaviate_class:
                schema_class["properties"] = self._get_primitive_properties(weaviate_class["properties"])

            # Add the item
            try:
                response = self._connection.run_rest("/schema/" + schema_class_type, REST_METHOD_POST, schema_class)
            except ConnectionError as conn_err:
                raise type(conn_err)(str(conn_err)
                                     + ' Connection error, class may not have been created properly.').with_traceback(
                    sys.exc_info()[2])
            if response.status_code != 200:
                raise UnexpectedStatusCodeException("Create class", response)

    def _get_primitive_properties(self, properties_list):
        """ Filters the list of properties for only primitive properties

        :param properties_list: A list of schema properties
        :type properties_list: list
        :return: a list of properties containing only primitives or an empty list
        """
        primitive_properties = []

        for property_ in properties_list:

            if not self._property_is_primitive(property_["dataType"]):
                # property is complex and therefore will be ignored
                continue

            # create the property object
            schema_property = {
                "dataType": property_["dataType"],
                "cardinality": property_["cardinality"],
                "description": property_["description"],
                "name": property_["name"]
            }

            # Check not mandetory fields
            if "index" in property_:
                schema_property["index"] = property_["index"]
            if "vectorizePropertyName" in property_:
                schema_property["vectorizePropertyName"] = property_["vectorizePropertyName"]

            # add keywords
            if "keywords" in property_:
                schema_property["keywords"] = property_["keywords"]

            primitive_properties.append(schema_property)

        return primitive_properties

    def _property_is_primitive(self, data_type_list):
        """ Checks if the property is primitive

        :param data_type_list: Data types of the property
        :type data_type_list: list
        :return: true if it only consists of primitive types
        """
        for data_type in data_type_list:
            if data_type not in _PRIMITIVE_WEAVIATE_TYPES:
                return False
        return True

    def _create_complex_properties(self, schema_class_type, schema_classes_list):
        """ Add crossreferences to already existing classes

        :param schema_class_type: can be found as constants e.g. SCHEMA_CLASS_TYPE_THINGS.
        :type schema_class_type: SCHEMA_CLASS_TYPE_THINGS or SCHEMA_CLASS_TYPE_ACTIONS
        :param schema_classes_list: classes as they are found in a schema json description.
        :type schema_classes_list: list
        :return: None if successful.
        :raises
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        for schema_class in schema_classes_list:
            for property_ in schema_class["properties"]:

                if self._property_is_primitive(property_["dataType"]):
                    continue

                # create the property object
                schema_property = {
                    "dataType": property_["dataType"],
                    "cardinality": property_["cardinality"],
                    "description": property_["description"],
                    "name": property_["name"]
                }

                if "index" in property_:
                    schema_property["index"] = property_["index"]
                if "vectorizePropertyName" in property_:
                    schema_property["vectorizePropertyName"] = property_["vectorizePropertyName"]

                # add keywords
                if "keywords" in property_:
                    schema_property["keywords"] = property_["keywords"]

                path = "/schema/"+schema_class_type+"/"+schema_class["class"]+"/properties"
                try:
                    response = self._connection.run_rest(path, REST_METHOD_POST, schema_property)
                except ConnectionError as conn_err:
                    raise type(conn_err)(str(conn_err)
                                         + ' Connection error, property may not have been created properly.'
                                         ).with_traceback(
                        sys.exc_info()[2])
                if response.status_code != 200:
                    raise UnexpectedStatusCodeException("Add properties to classes", response)

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

    def get_schema(self):
        """ Get the schema in weaviate

        :return: a dict containing the schema.
                 The schema may be empty. To see if a schema has already been loaded use contains_schema.
        :raises:
            ConnectionError: In case of network issues.
        """
        try:
            response = self._connection.run_rest("/schema", REST_METHOD_GET)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, schema could not be retrieved.'
                                 ).with_traceback(
                sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Get schema", response)

    def contains_schema(self, schema=None):
        """ To check if weaviate already contains a schema.

        :param schema: if a schema is given it is checked if this
            specific schema is already loaded. It will test only this schema.
            If the given schema is a subset of the loaded schema it will still return true.
        :return: True if a schema is present otherwise False
        :rtype: bool
        :raises:
            ConnectionError: In case of network issues.
        """
        loaded_schema = self.get_schema()

        if schema is not None:
            return _is_sub_schema(schema, loaded_schema)

        if len(loaded_schema["things"]["classes"]) > 0 or len(loaded_schema["actions"]["classes"]) > 0:
            return True

        return False

    def delete_thing(self, uuid):
        """

        :param uuid: ID of the thing that should be removed from the graph.
        :type uuid: str
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
            response = self._connection.run_rest("/things/" + uuid, REST_METHOD_DELETE)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, thing could not be deleted.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 204:
            return  # Successfully deleted
        else:
            raise UnexpectedStatusCodeException("Delete thing", response)

    def delete_reference_from_thing(self, from_thing_uuid, from_property_name, to_thing_uuid, to_weaviate="localhost"):
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

        if not isinstance(from_thing_uuid, str) or not isinstance(to_thing_uuid, str):
            raise TypeError("UUID must be of type str")
        if not validators.uuid(from_thing_uuid) or not validators.uuid(to_thing_uuid):
            raise ValueError("UUID has no proper form")
        if not isinstance(from_property_name, str):
            raise TypeError("Property name must be type str")
        if not isinstance(to_weaviate, str):
            raise TypeError("To weaviate must be type str")

        beacon = {
            "beacon": "weaviate://" + to_weaviate + "/things/" + to_thing_uuid
        }

        path = "/things/" + from_thing_uuid + "/references/" + from_property_name

        try:
            response = self._connection.run_rest(path, REST_METHOD_DELETE, beacon)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, thing could not be deleted.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 204:
            return  # Successfully deleted
        else:
            raise UnexpectedStatusCodeException("Delete property from thing", response)

    def extend_c11y(self, concept, definition, weight=1.0):
        """ Extend the c11y with new concepts

        :param concept: The new concept that should be added, e.g. an abbreviation.
        :type concept: str
        :param definition: The definition of the new concept.
        :type definition: str
        :param weight: The weight of the new definition compared to the old one.
        :type weight: float
        :return: None if successful
        """

        if not isinstance(concept, str):
            raise TypeError("Concept must be string")
        if not isinstance(definition, str):
            raise TypeError("Definition must be string")
        if not isinstance(weight, float):
            raise TypeError("Weight must be float")

        if weight > 1.0 or weight < 0.0:
            raise ValueError("Weight out of limits 0.0 <= weight <= 1.0")

        extension = {
            "concept": concept,
            "definition": definition,
            "weight": weight
        }

        try:
            response = self._connection.run_rest("/c11y/extensions/", REST_METHOD_POST, extension)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, c11y could not be extended.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return  # Successfully extended
        else:
            raise UnexpectedStatusCodeException("Extend c11y", response)


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

