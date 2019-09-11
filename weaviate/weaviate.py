from .connect import *
from .exceptions import *


class Weaviate:

    # New weaviate client
    def __init__(self, url, auth_client_secret=""):
        # TODO check if url is right form
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
            raise ConnectionError

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
                print("WARNING: STATUS CODE WAS NOT 200 but " + str(response.status_code) + " with: " + str(
                    response.json()))
                raise UnexpectedStatusCodeException
