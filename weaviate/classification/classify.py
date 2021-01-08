import sys
import validators
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from weaviate.connect import REST_METHOD_GET, Connection
from .config_builder import ConfigBuilder

class Classification:
    """
    Classification class used to schedule and/or check the status of
    a classification process of weaviate objects.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Classification class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection

    def schedule(self) -> ConfigBuilder:
        """
        Schedule a Classification of the Objects within weaviate.

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
            A dict containing the weaviate answer.

        Raises
        ------
        ValueError
            If not a proper uuid.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not validators.uuid(classification_uuid):
            raise ValueError("Given UUID does not have a proper form")

        try:
            response = self._connection.run_rest("/classifications/" + classification_uuid,\
                                                                         REST_METHOD_GET)
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, classification status could not be retrieved.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
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

    def _check_status(self,
            classification_uuid: str,
            status: str
        ) -> bool:
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
