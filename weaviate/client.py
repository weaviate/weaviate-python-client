import sys
import validators

from .connect import *
from .exceptions import *
from .util import _get_dict_from_object
from requests.exceptions import ConnectionError

SCHEMA_CLASS_TYPE_THINGS = "things"
SCHEMA_CLASS_TYPE_ACTIONS = "actions"


class Client:
    """ A python native weaviate client
    """

    def __init__(self, url, auth_client_secret=""):
        """ New weaviate client

        :param url: To the weaviate instance.
        :type url: str
        :param auth_client_secret: Authentification client secret.
        :type auth_client_secret: str
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

        self.connection = connection.Connection(url=url, auth_client_secret=auth_client_secret)

    def create_thing(self, thing, class_name, uuid=None):
        """ Takes a dict describing the thing and adds it to weaviate

        :param thing: Thing to be added.
        :type thing: dict
        :param class_name: Associated with the thing given.
        :type class_name: str
        :param uuid: Thing will be created under this uuid if it is provided.
        :type uuid: str
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
            raise TypeError("Expected class_name of type str but was: "+str(type))

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

        try:
            response = self.connection.run_rest("/things", REST_METHOD_POST, weaviate_obj)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, thing was not added to weaviate.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()["id"]

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
        :return: None if successful.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        path = "/batching/things"

        try:
            response = self.connection.run_rest(path, REST_METHOD_POST, things_batch_request.get_request_body())
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, batch was not added to weaviate.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return

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
            response = self.connection.run_rest("/things/"+uuid, REST_METHOD_PATCH, payload)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, thing was not patched.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 204:
            return None  # success
        else:
            raise UnexpectedStatusCodeException("PATCH merge of thing not successful", response)

    def add_reference_to_thing(self, from_thing_uuid, from_property_name, to_thing_uuid, to_weaviate="localhost"):
        """ Allows to link two objects unidirectionally.

        :param from_thing_uuid: the thing that should have the reference as part of its properties.
        :type from_thing_uuid: str in the form of an UUID
        :param from_property_name: the name of the property within the thing.
        :type from_property_name: str
        :param to_thing_uuid: the UUID of the thing that should be referenced.
        :type to_thing_uuid: str in the form of an UUID
        :param to_weaviate: specifies the weaviate instance on which the cross referenced thing is loacated
        :type to_weaviate: str
        :return: None if successful.
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.

        """

        # TODO Add type and value checks

        # Create the beacon
        beacon = {
            "beacon": "weaviate://"+to_weaviate+"/things/"+to_thing_uuid
        }

        path = "/things/" + from_thing_uuid + "/references/" + from_property_name

        try:
            response = self.connection.run_rest(path, REST_METHOD_POST, beacon)
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
            response = self.connection.run_rest("/things/"+uuid, REST_METHOD_PUT, weaviate_obj)
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
        :return: None
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        if reference_batch_request.get_batch_size() == 0:
            return  # No data in batch

        path = "/batching/references"

        try:
            response = self.connection.run_rest(path, REST_METHOD_POST, reference_batch_request.get_request_body())
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, reference was not added to weaviate.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return
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
            response = self.connection.run_rest("/things/"+uuid_thing, REST_METHOD_GET, params=params)
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
            response = self.connection.run_rest(path, REST_METHOD_GET)
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
        """
        try:
            loaded_schema = _get_dict_from_object(schema)
        except ConnectionError:
            raise
        except UnexpectedStatusCodeException:
            raise

        # TODO validate the schema e.g. small parser?

        if SCHEMA_CLASS_TYPE_THINGS in loaded_schema:
            self._create_class(SCHEMA_CLASS_TYPE_THINGS, loaded_schema[SCHEMA_CLASS_TYPE_THINGS]["classes"])
        if SCHEMA_CLASS_TYPE_ACTIONS in loaded_schema:
            self._create_class(SCHEMA_CLASS_TYPE_ACTIONS, loaded_schema[SCHEMA_CLASS_TYPE_ACTIONS]["classes"])
        if SCHEMA_CLASS_TYPE_THINGS in loaded_schema:
            self._create_properties(SCHEMA_CLASS_TYPE_THINGS, loaded_schema[SCHEMA_CLASS_TYPE_THINGS]["classes"])
        if SCHEMA_CLASS_TYPE_ACTIONS in loaded_schema:
            self._create_properties(SCHEMA_CLASS_TYPE_ACTIONS, loaded_schema[SCHEMA_CLASS_TYPE_ACTIONS]["classes"])

    def _create_class(self, schema_class_type, schema_classes_list):
        """ Create all the classes in the list.
        This function does not create properties,
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

            schema_class = {
                "class": weaviate_class['class'],
                "description": weaviate_class['description'],
                "properties": [],
                "keywords": []
            }

            # Add the item
            try:
                response = self.connection.run_rest("/schema/"+schema_class_type, REST_METHOD_POST, schema_class)
            except ConnectionError as conn_err:
                raise type(conn_err)(str(conn_err)
                                     + ' Connection error, class may not have been created properly.').with_traceback(
                    sys.exc_info()[2])
            if response.status_code != 200:
                raise UnexpectedStatusCodeException("Create class", response)

    def _create_properties(self, schema_class_type, schema_classes_list):
        """ Create all the properties in the list.
        Make sure that all necessary classes have been created first.
        See _create_class

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

                # create the property object
                schema_property = {
                    "dataType": [],
                    "cardinality": property_["cardinality"],
                    "description": property_["description"],
                    "name": property_["name"]
                }

                if "index" in property_:
                    schema_property["index"] = property_["index"]

                # add the dataType(s)
                for datatype in property_["dataType"]:
                    schema_property["dataType"].append(datatype)

                # add keywords
                if "keywords" in property_:
                    schema_property["keywords"] = property_["keywords"]

                path = "/schema/"+schema_class_type+"/"+schema_class["class"]+"/properties"
                try:
                    response = self.connection.run_rest(path, REST_METHOD_POST, schema_property)
                except ConnectionError as conn_err:
                    raise type(conn_err)(str(conn_err)
                                         + ' Connection error, property may not have been created properly.'
                                         ).with_traceback(
                        sys.exc_info()[2])
                if response.status_code != 200:
                    raise UnexpectedStatusCodeException("Add properties to classes", response)

    def start_knn_classification(self, schema_class_name, k, based_on_properties, classify_properties):
        """ Starts a knn classification based on the given parameters.

        :param schema_class_name: Class on which the classification is executed.
        :type schema_class_name: str
        :param k: the number of nearest neighbours that are taken into account for the classification.
        :type k: int
        :param based_on_properties: The property or the properties that are used to for the classification.
                                    This field is compared to the other fields and serves as the decision base.
        :type based_on_properties:  str, list of str
        :param classify_properties: The property or the properties that are labeled (the classes).
        :type classify_properties: str, list of str
        :return: dict with the status of the classification.
        :raises:
            TypeError: if argument is of wrong type.
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        if not isinstance(schema_class_name, str):
            raise TypeError("Schema class name must be of type string")
        if not isinstance(k, int):
            raise TypeError("K must be of type integer")
        if isinstance(based_on_properties, str):
            based_on_properties = [based_on_properties]
        if isinstance(classify_properties, str):
            classify_properties = [classify_properties]
        if not isinstance(based_on_properties, list):
            raise TypeError("Based on properties must be of type string or list of strings")
        if not isinstance(classify_properties, list):
            raise TypeError("Classify properties must be of type string or list of strings")

        payload = {
            "class": schema_class_name,
            "k": k,
            "basedOnProperties": based_on_properties,
            "classifyProperties": classify_properties
        }

        try:
            response = self.connection.run_rest("/classifications", REST_METHOD_POST, payload)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, classification may not started.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 201:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Start classification", response)

    def get_knn_classification_status(self, classification_uuid):
        """ Polls the current state of the given classification

        :param classification_uuid: identifier of the classification.
        :type classification_uuid: str
        :return: a dict containing the weaviate answer.
        :raises:
            ValueError: if not a proper uuid.
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        if not validators.uuid(classification_uuid):
            raise ValueError("Given UUID does not have a proper form")

        try:
            response = self.connection.run_rest("/classifications/"+classification_uuid, REST_METHOD_GET)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, classification status could not be retrieved.'
                                 ).with_traceback(
                sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Get classification status", response)

    def is_classification_complete(self, classification_uuid):
        """ Checks if a previously started classification job has completed.

        :param classification_uuid: identifier of the classification.
        :return: true if given classification has finished.
        """
        try:
            response = self.get_knn_classification_status(classification_uuid)
        except ConnectionError:
            return False
        if response["status"] == "completed":
            return True
        return False

    def is_reachable(self):
        """ Ping weaviate

        :return: True if weaviate could be reached False otherwise.
        """
        try:
            response = self.connection.run_rest("/meta", REST_METHOD_GET)
            if response.status_code == 200 or response.status_code == 401:
                response = self.connection.run_rest("/things", REST_METHOD_GET, params={"limit":1})
                if response.status_code == 200 or response.status_code == 401:
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
            response = self.connection.run_rest("/schema", REST_METHOD_GET)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, schema could not be retrieved.'
                                 ).with_traceback(
                sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Get schema", response)

    def contains_schema(self):
        """ To check if weaviate already contains a schema.

        :return: True if a schema is present otherwise False
        :raises:
            ConnectionError: In case of network issues.
        """

        schema = self.get_schema()

        if len(schema["things"]["classes"]) > 0 or len(schema["actions"]["classes"]) > 0:
            return True

        return False

    def delete_thing(self, uuid):

        if not isinstance(uuid, str):
            raise TypeError("UUID must be type str")
        if not validators.uuid(uuid):
            raise ValueError("UUID does not have proper form")

        try:
            response = self.connection.run_rest("/things/"+uuid, REST_METHOD_DELETE)
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
            response = self.connection.run_rest(path, REST_METHOD_DELETE, beacon)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, thing could not be deleted.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 204:
            return  # Successfully deleted
        else:
            raise UnexpectedStatusCodeException("Delete property from thing", response)
