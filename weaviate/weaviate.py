import json
import os
import requests

import validators

from .connect import *
from .exceptions import *

SCHEMA_CLASS_TYPE_THINGS = "things"
SCHEMA_CLASS_TYPE_ACTIONS = "actions"

class Weaviate:

    # New weaviate client
    def __init__(self, url, auth_client_secret=""):
        if url is None:
            raise ValueError("URL is expected to be string but is None")
        if not isinstance(url, str):
            raise ValueError("URL is expected to be string but is "+str(type(url)))
        if not validators.url(url):
            raise ValueError("URL has no propper form: "+url)
        self.connection = connection.Connection(url=url, auth_client_secret=auth_client_secret)

    # Takes a dict describing the thing and adds it to weaviate
    # The thing is associated with the class given in class_name
    # If an uuid is given the thing will be created under this uuid
    # Returns the id of the created thing if successful
    def create_thing(self, thing, class_name, uuid=None):

        weaviate_obj = {
            "class": class_name,
            "schema": thing
        }
        if uuid is not None:
            weaviate_obj["id"] = uuid

        try:
            response = self.connection.run_rest("/things", REST_METHOD_POST, weaviate_obj)
        except ConnectionError as conn_err:
            print("Connection error, thing was not added to weaviate: " + str(conn_err))
            raise

        if response.status_code == 200:
            return response.json()["id"]

        else: #TODO catch all status codes
            thing_does_already_exist = False
            try:
                if 'already exists' in response.json()['error'][0]['message']:
                    thing_does_already_exist = True
            except KeyError:
                pass
            except Exception as e:
                print('Unexepected exception: ' + str(e))
                raise Exception

            if thing_does_already_exist:
                raise ThingAlreadyExistsException

            print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                response.json()))


            raise UnexpectedStatusCodeException

    # Updates an already existing thing
    # thing contains a dict describing the new values
    def update_thing(self, thing, class_name, uuid):

        weaviate_obj = {
            "id": uuid,
            "class": class_name,
            "schema": thing
        }

        try:
            response = self.connection.run_rest("/things/"+uuid, REST_METHOD_PUT, weaviate_obj)
        except ConnectionError as conn_err:
            print("Connection error, thing was not updated: " + str(conn_err))
            raise ConnectionError

        if response.status_code == 200:
            return

        else: #TODO catch all status codes

            print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                response.json()))

            raise UnexpectedStatusCodeException

    # Add a property reference to a thing
    # thing_uuid the thing that should have the reference as part of its properties
    # the name of the property within the thing
    # The beacon dict takes the form: [{
    #                     "beacon": "weaviate://localhost/things/uuid",
    #                     ...
    #                 }]
    def add_property_reference_to_thing(self, thing_uuid, property_name, property_beacons):

        path = "/things/" + thing_uuid + "/references/" + property_name

        try:
            response = self.connection.run_rest(path, REST_METHOD_POST, property_beacons)
        except ConnectionError as conn_err:
            print("Connection error, reference was not added to weaviate: " + str(conn_err))
            raise

        if response.status_code == 200:
            return
        elif response.status_code == 401:
            raise UnauthorizedRequest401Exception
        elif response.status_code == 403:
            raise ForbiddenRequest403Exception
        elif response.status_code == 422:
            raise SemanticError422Exception
        elif response.status_code == 500:
            raise ServerError500Exception(response.json())
        else:
            print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                response.json()))
            raise UnexpectedStatusCodeException

    # Batchloading references
    # Takes four lists that describe references.
    def add_references_in_batch(self, reference_batch_request):
        if reference_batch_request.get_batch_size() == 0:
            return  # No data in batch

        path = "/batching/references"

        try:
            response = self.connection.run_rest(path, REST_METHOD_POST, reference_batch_request.get_request_body())
        except ConnectionError as conn_err:
            print("Connection error, reference was not added to weaviate: " + str(conn_err))
            raise

        if response.status_code == 200:
            return
        elif response.status_code == 401:
            raise UnauthorizedRequest401Exception
        elif response.status_code == 403:
            raise ForbiddenRequest403Exception
        elif response.status_code == 422:
            raise SemanticError422Exception
        elif response.status_code == 500:
            raise ServerError500Exception(response.json())
        else:
            print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                response.json()))
            raise UnexpectedStatusCodeException

    # Returns true if a thing exists in weaviate
    def thing_exists(self, uuid_thing):
        if not isinstance(uuid_thing, str):
            uuid_thing = str(uuid_thing)
        try:
            response = self.connection.run_rest("/things/"+uuid_thing, REST_METHOD_GET)
        except ConnectionError as conn_err:
            print("Connection error not sure if thing exists")
            raise

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                response.json()))
            raise UnexpectedStatusCodeException

    # Retrieves the vector representation of the given word
    # The word can be CamelCased for a compound vector
    # Returns the vector or throws and error, the vector might be empty if the c11y does not contain it
    def get_c11y_vector(self, word):
        path = "/c11y/words/" + word
        try:
            response = self.connection.run_rest(path, REST_METHOD_GET)
        except AttributeError:

            raise
        except Exception as e:
            print("(TODO add specific catch for this exception) Connection error, reference was not added to weaviate: " + str(e))
            raise
        else:
            if response.status_code == 200:
                return response.json()
            else:
                #print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                #    response.json()))
                raise UnexpectedStatusCodeException

    # Create the schema at the weaviate instance
    # schema can either be the path to a json file, a url of a json file or a dict
    # throws exceptions:
    # - ValueError if input is wrong
    # - IOError if file could not be read
    def create_schema(self, schema):
        loaded_schema = None

        # check if things files is url
        if schema == None:
            raise ValueError("Schema is None")

        if isinstance(schema, dict):
            # Schema is already a dict
            loaded_schema = schema
        elif isinstance(schema, str):

            if validators.url(schema):
                # Schema is URL
                f = requests.get(schema)
                if f.status_code == 200:
                    loaded_schema = f.json()
                else:
                    raise ValueError("Could not download file")

            elif not os.path.isfile(schema):
                # Schema is neither file nor URL
                raise ValueError("No schema file found at location")
            else:
                # Schema is file
                try:
                    with open(schema, 'r') as file:
                        loaded_schema = json.load(file)
                except IOError:
                    raise
        else:
            raise ValueError("Schema is not of a supported type. Supported types are url or file path as string or schema as dict.")


        # TODO validate schema

        self._create_class(SCHEMA_CLASS_TYPE_THINGS, loaded_schema[SCHEMA_CLASS_TYPE_THINGS]["classes"])
        self._create_class(SCHEMA_CLASS_TYPE_ACTIONS, loaded_schema[SCHEMA_CLASS_TYPE_ACTIONS]["classes"])
        self._create_properties(SCHEMA_CLASS_TYPE_THINGS, loaded_schema[SCHEMA_CLASS_TYPE_THINGS]["classes"])
        self._create_properties(SCHEMA_CLASS_TYPE_ACTIONS, loaded_schema[SCHEMA_CLASS_TYPE_ACTIONS]["classes"])


    # Create all the classes in the list
    # This function does not create properties,
    # to avoid references to classes that do not yet exist
    # Takes:
    # - schema_class_type which can be found as constants in this file
    # - schema_classes_list a list of classes as it is found in a schema json description
    def _create_class(self, schema_class_type, schema_classes_list):

        for weaviate_class in schema_classes_list:

            schema_class = {
                "class": weaviate_class['class'],
                "description": weaviate_class['description'],
                "properties": [],
                "keywords": []
            }

            # Add the item
            self.connection.run_rest("/schema/"+schema_class_type, REST_METHOD_POST, schema_class)

    def _create_properties(self, schema_class_type, schema_classes_list):
        for schema_class in schema_classes_list:
            for property in schema_class["properties"]:

                # create the property object
                schema_property = {
                    "dataType": [],
                    "cardinality": property["cardinality"],
                    "description": property["description"],
                    "name": property["name"]
                }

                # add the dataType(s)
                for datatype in property["dataType"]:
                    schema_property["dataType"].append(datatype)

                # add keywords
                if "keywords" in property:
                    schema_property["keywords"] = property["keywords"]

                path = "/schema/"+schema_class_type+"/"+schema_class["class"]+"/properties"
                self.connection.run_rest(path, REST_METHOD_POST, schema_property)

    # Starts a knn classification based on the given parameters
    # Returns a dict with the answer from weaviate
    def start_knn_classification(self, schema_class_name, k, based_on_properties, classify_properties):
        if not isinstance(schema_class_name, str):
            raise ValueError("Schema class name must be of type string")
        if not isinstance(k, int):
            raise ValueError("K must be of type integer")
        if isinstance(based_on_properties, str):
            based_on_properties = [based_on_properties]
        if isinstance(classify_properties, str):
            classify_properties = [classify_properties]
        if not isinstance(based_on_properties, list):
            raise ValueError("Based on properties must be of type string or list of strings")
        if not isinstance(classify_properties, list):
            raise ValueError("Classify properties must be of type string or list of strings")

        payload = {
            "class": schema_class_name,
            "k": k,
            "basedOnProperties": based_on_properties,
            "classifyProperties": classify_properties
        }

        response = self.connection.run_rest("/classifications", REST_METHOD_POST, payload)

        if response.status_code == 201:
            return response.json()
        else:
            print("WARNING: STATUS CODE WAS NOT 201 but " + str(response.status_code) + " with: " + str(
                response.json()))
            raise UnexpectedStatusCodeException

    # Polls the current state of the given classification
    # Returns a dict containing the weaviate answer
    def get_knn_classification_status(self, classification_uuid):
        if not validators.uuid(classification_uuid):
            raise ValueError("Given UUID does not have a proper form")

        response = self.connection.run_rest("/classifications/"+classification_uuid, REST_METHOD_GET)
        if response.status_code == 200:
            return response.json()
        else:
            print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                response.json()))
            raise UnexpectedStatusCodeException

    # Returns true if the classification has finished
    def is_classification_complete(self, classification_uuid):
        response = self.get_knn_classification_status(classification_uuid)
        if response["status"] == "completed":
            return True
        return False

    # # Queries the instance with a
    # def query(self, gql):
