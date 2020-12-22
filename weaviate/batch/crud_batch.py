import sys
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.connect import REST_METHOD_POST

class Batch:
    """
    Batch class used to add multiple objects or object references at once into weaviate.
    """

    def __init__(self,
            connection: 'weaviate.connect.Connection'
        ):
        """
        Initialize a Batch class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection

    def create_objects(self,
            objects_batch_request: 'weaviate.batch.ObjectsBatchReques'
        ) -> list:
        """
        Creates multiple objects at once in weaviate

        Parameters
        ----------
        objects_batch_request : weaviate.batch.ObjectsBatchRequest
            The batch of objects that should be added.

        Returns
        -------
        list
            A list with the status of every thing that was created.
        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        path = "/batch/"

        try:
            response = self._connection.run_rest(
                path=path,
                rest_method=REST_METHOD_POST,
                weaviate_object=objects_batch_request.get_request_body()
                )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                        + ' Connection error, batch was not added to weaviate.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException("Create objects in batch", response)


    def add_references(self,
            reference_batch_request: 'weaviate.batch.ReferenceBatchRequest'
        ) -> list:
        """
        Batch loading references.
        Loading batch references is faster by ignoring some validations.
        Loading inconsistent data may ends up in an invalid graph.
        If the consistency of the references is wanted use
        'Client().data_object.reference.add' to have additional validation instead.

        Parameters
        ----------
        reference_batch_request : weaviate.batch.ReferenceBatchRequest
            Contains all the references that should be added in one batch.

        Returns
        -------
        list, optional
            A list with the status of every reference added or None if no
            reference in the 'reference_batch_request'.

        Raises
        ------
        type
            If the network connection to weaviate fails.
        UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if reference_batch_request.get_batch_size() == 0:
            return None # No data in batch

        path = "/batch/references"

        try:
            response = self._connection.run_rest(
                path=path,
                rest_method=REST_METHOD_POST,
                weaviate_object=reference_batch_request.get_request_body()
                )
        except ConnectionError as conn_err:
            message = str(conn_err)\
                        + ' Connection error, reference was not added to weaviate.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException("Add references in batch", response)
