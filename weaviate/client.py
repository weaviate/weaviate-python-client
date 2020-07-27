import sys

from .connect import *
from .classify import Classification
from .exceptions import *
from .client_config import ClientConfig
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_THINGS

# Class is splitted into multiple files

from weaviate._client_create_update_entity import _create, \
    _create_actions_in_batch, _create_things_in_batch, _patch, _put
from weaviate._client_schema import _create_schema, _contains_schema, _get_schema
# TODO _create_complex_properties, _property_is_primitive, _get_primitive_properties, _create_class_with_primitives
from weaviate._client_crud_reference import _add_reference, _add_references_in_batch, _delete_reference
from weaviate._client_read_delete_entity import _exists, _get, _delete
from weaviate._client_c11y import _get_c11y_vector, _extend_c11y

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
            return response.json()  # Successfully queried
        else:
            raise UnexpectedStatusCodeException("GQL query", response)

    # Implement the following functions in seperate files but keep a method in the client
    # for better ide recognition of `self`

    # Create and update
    def create(self, entity, class_name, uuid=None, semantic_type=SEMANTIC_TYPE_THINGS, vector_weights=None):
        return _create(self, entity, class_name, uuid, semantic_type, vector_weights)

    def create_actions_in_batch(self, actions_batch_request):
        return _create_actions_in_batch(self, actions_batch_request)

    def create_things_in_batch(self, things_batch_request):
        return _create_things_in_batch(self, things_batch_request)

    def patch(self, entity, class_name, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
        return _patch(self, entity, class_name, uuid, semantic_type)

    def put(self, entity, class_name, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
        return _put(self, entity, class_name, uuid, semantic_type)

    # Contextionary
    def extend_c11y(self, concept, definition, weight=1.0):
        return _extend_c11y(self, concept, definition, weight)

    def get_c11y_vector(self, word):
        return _get_c11y_vector(self, word)

    # Schema
    def create_schema(self, schema):
        return _create_schema(self, schema)

    def contains_schema(self, schema=None):
        return _contains_schema(self, schema)

    def get_schema(self):
        return _get_schema(self)

    # CRUD Reference
    def add_reference(self, from_uuid, from_property_name, to_uuid,
                      from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS,
                      to_weaviate="localhost"):
        return _add_reference(self, from_uuid, from_property_name, to_uuid,
                       from_semantic_type, to_semantic_type,
                       to_weaviate)

    def add_references_in_batch(self, reference_batch_request):
        return _add_references_in_batch(self, reference_batch_request)

    def delete_reference(self, from_uuid, from_property_name, to_uuid,
                         from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS,
                         to_weaviate="localhost"):
        return _delete_reference(self, from_uuid, from_property_name, to_uuid,
                          from_semantic_type, to_semantic_type,
                          to_weaviate)

    def exists(self, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
        return _exists(self, uuid, semantic_type)

    def get(self, uuid, meta=False, semantic_type=SEMANTIC_TYPE_THINGS):
        return _get(self, uuid, meta, semantic_type)

    def delete(self, uuid, semantic_type=SEMANTIC_TYPE_THINGS):
        return _delete(self, uuid, semantic_type)
