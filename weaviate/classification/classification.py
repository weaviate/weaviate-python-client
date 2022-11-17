"""
Classification class definition.
"""
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import get_valid_uuid
from .config_builder import ConfigBuilder


class Classification:
    """
    Classification class used to schedule and/or check the status of
    a classification process of Weaviate objects.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Classification class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        """

        self._connection = connection

    def schedule(self) -> ConfigBuilder:
        """
        Schedule a Classification of the Objects within Weaviate.

        Returns
        -------
        weaviate.classification.config_builder.ConfigBuilder
            A ConfigBuilder that should be configured to the desired
            classification task
        """

        return ConfigBuilder(self._connection, self)

    def get(self, classification_uuid: str) -> dict:
        """
        Polls the current state of the given classification.

        Parameters
        ----------
        classification_uuid : str
            Identifier of the classification.

        Returns
        -------
        dict
            A dict containing the Weaviate answer.

        Raises
        ------
        ValueError
            If not a proper uuid.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        classification_uuid = get_valid_uuid(classification_uuid)

        try:
            response = self._connection.get(
                path="/classifications/" + classification_uuid,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Classification status could not be retrieved."
            ) from conn_err
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException("Get classification status", response)

    def is_complete(self, classification_uuid: str) -> bool:
        """
        Checks if a started classification job has completed.

        Parameters
        ----------
        classification_uuid : str
            Identifier of the classification.

        Returns
        -------
        bool
            True if given classification has finished, False otherwise.
        """

        return self._check_status(classification_uuid, "completed")

    def is_failed(self, classification_uuid: str) -> bool:
        """
        Checks if a started classification job has failed.

        Parameters
        ----------
        classification_uuid : str
            Identifier of the classification.

        Returns
        -------
        bool
            True if the classification failed, False otherwise.
        """

        return self._check_status(classification_uuid, "failed")

    def is_running(self, classification_uuid: str) -> bool:
        """
        Checks if a started classification job is running.

        Parameters
        ----------
        classification_uuid : str
            Identifier of the classification.

        Returns
        -------
        bool
            True if the classification is running, False otherwise.
        """

        return self._check_status(classification_uuid, "running")

    def _check_status(self, classification_uuid: str, status: str) -> bool:
        """
        Check for a status of a classification.

        Parameters
        ----------
        classification_uuid : str
            Identifier of the classification.
        status : str
            Status to check for.

        Returns
        -------
        bool
            True if 'status' is satisfied, False otherwise.
        """

        try:
            response = self.get(classification_uuid)
        except RequestsConnectionError:
            return False
        if response["status"] == status:
            return True
        return False
