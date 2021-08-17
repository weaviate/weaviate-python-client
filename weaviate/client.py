"""
Client class definition.
"""
from typing import Optional, Tuple, Union
from numbers import Real
from .auth import AuthCredentials
from .exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from .connect import Connection
from .classification import Classification
from .schema import Schema
from .contextionary import Contextionary
from .batch import Batch
from .data import DataObject
from .gql import Query


class Client:
    """
    A python native weaviate Client class that encapsulates Weaviate functionalities in one object.
    A Client instance creates all the needed objects to interact with Weaviate, and connects all of
    them to the same Weaviate instance. See below the Attributes of the Client instance. For the
    per attribute functionality see that attribute's documentation.

    Attributes
    ----------
    classification : weaviate.classification.Classification
        A Classification object instance connected to the same Weaviate instance as the Client.
    schema : weaviate.schema.Schema
        A Schema object instance connected to the same Weaviate instance as the Client.
    contextionary : weaviate.contextionary.Contextionary
        A Contextionary object instance connected to the same Weaviate instance as the Client.
    batch : weaviate.batch.Batch
        A Batch object instance connected to the same Weaviate instance as the Client.
    data_object : weaviate.date.DataObject
        A DataObject object instance connected to the same Weaviate instance as the Client.
    query : weaviate.gql.Query
        A Query object instance connected to the same Weaviate instance as the Client.
    """

    def __init__(self,
            url: str,
            auth_client_secret: AuthCredentials=None,
            timeout_config: Union[Tuple[Real, Real], Real]=(2, 20)
        ):
        """
        Initialize a Client class instance.

        Parameters
        ----------
        url : str
            The URL to the weaviate instance.
        auth_client_secret : weaviate.AuthCredentials, optional
            Authentication client secret, by default None.
        timeout_config : tuple(Real, Real) or Real, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            real number or, a tuple of two real numbers: (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value, by default (2, 20).

        Examples
        --------
        Without Auth.

        >>> client = Client(
        ...     url = 'http://localhost:8080'
        ... )
        >>> client = Client(
        ...     url = 'http://localhost:8080',
        ...     timeout_config = (5, 15)
        ... )

        With Auth.

        >>> my_credentials = weaviate.auth.AuthClientPassword(USER_NAME, MY_PASSWORD)
        >>> client = Client(
        ...     url = 'http://localhost:8080',
        ...     auth_client_secret = my_credentials
        ... )

        Raises
        ------
        TypeError
            If arguments are of a wrong data type.
        """

        if not isinstance(url, str):
            raise TypeError("URL is expected to be string but is " + str(type(url)))
        if url.endswith("/"):
            # remove trailing slash
            url = url[:-1]

        self._connection = Connection(
            url=url,
            auth_client_secret=auth_client_secret,
            timeout_config=timeout_config
        )
        self.classification = Classification(self._connection)
        self.schema = Schema(self._connection)
        self.contextionary = Contextionary(self._connection)
        self.batch = Batch(self._connection)
        self.data_object = DataObject(self._connection)
        self.query = Query(self._connection)

    def is_ready(self) -> bool:
        """
        Ping Weaviate's ready state

        Returns
        -------
        bool
            True if Weaviate is ready to accept requests,
            False otherwise.
        """

        try:
            response = self._connection.get(path="/.well-known/ready")
            if response.status_code == 200:
                return True
            return False
        except RequestsConnectionError:
            return False

    def is_live(self) -> bool:
        """
        Ping Weaviate's live state.

        Returns
        --------
        bool
            True if weaviate is live and should not be killed,
            False otherwise.
        """

        response = self._connection.get(path="/.well-known/live")
        if response.status_code == 200:
            return True
        return False

    def get_meta(self) -> dict:
        """
        Get the meta endpoint description of weaviate.

        Returns
        -------
        dict
            The dict describing the weaviate configuration.

        Raises
        ------
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        response = self._connection.get(path="/meta")
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException("Meta endpoint", response)

    def get_open_id_configuration(self) -> Optional[dict]:
        """
        Get the openid-configuration.

        Returns
        -------
        dict
            The configuration or None if not configured.

        Raises
        ------
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        response = self._connection.get(path="/.well-known/openid-configuration")
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Meta endpoint", response)

    @property
    def timeout_config(self) -> Tuple[Real, Real]:
        """
        Getter/setter for `timeout_config`.

        Parameters
        ----------
        timeout_config : tuple(Real, Real) or Real, optional
            For Getter only: Set the timeout configuration for all requests to the Weaviate server.
            It can be a real number or, a tuple of two real numbers:
                    (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value.

        Returns
        -------
        Tuple[Real, Real]
            For Getter only: Requests Timeout configuration.
        """

        return self._connection.timeout_config

    @timeout_config.setter
    def timeout_config(self, timeout_config: Union[Tuple[Real, Real], Real]):
        """
        Setter for `timeout_config`. (docstring should be only in the Getter)
        """

        self._connection.timeout_config = timeout_config
