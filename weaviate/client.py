from .connect import *
from .classification import Classification
from .schema import Schema
from .contextionary import Contextionary
from .batch import Batch
from .data import DataObject
from .gql import Query
from .client_config import ClientConfig
from requests.exceptions import ConnectionError


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
        self.schema = Schema(self._connection)
        self.contextionary = Contextionary(self._connection)
        self.batch = Batch(self._connection)
        self.data_object = DataObject(self._connection)
        self.query = Query(self._connection)

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


