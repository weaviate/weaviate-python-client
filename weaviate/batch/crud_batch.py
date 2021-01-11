import sys
import warnings
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.connect import REST_METHOD_POST, Connection
from .requests import BatchRequest, ObjectsBatchRequest, ReferenceBatchRequest

class Batch:
    """
    Batch class used to add multiple objects or object references at once into weaviate.
    """

    def __init__(self,connection: Connection):
        """
        Initialize a Batch class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection

    def create(self, batch_request: BatchRequest) -> list:
        """
        Load data objects in batches, either Objects or References.
        Loading batch References is faster by ignoring some validations.
        Loading inconsistent data may ends up in an invalid graph.
        If the consistency of the References is wanted use
        'Client().data_object.reference.add' to have additional validation instead.

        Parameters
        ----------
        batch_request : weaviate.batch.BatchRequest
            Contains all the data objects that should be added in one batch.
            Note: Should be a sub-class of BatchRequest since BatchRequest
            is just an abstract class.

        Returns
        -------
        list
            A list with the status of every data object added.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if isinstance(batch_request, ObjectsBatchRequest):
            data_object_type = "objects"
        elif isinstance(batch_request, ReferenceBatchRequest):
            data_object_type = "references"
        else:
            raise TypeError("Wrong argument type, expected a sub-class of BatchRequest \
                    (ObjectsBatchRequest or ReferenceBatchRequest), got: " +\
                    str(type(batch_request)))

        path = f"/batch/{data_object_type}"

        try:
            response = self._connection.run_rest(
                path=path,
                rest_method=REST_METHOD_POST,
                weaviate_object=batch_request.get_request_body()
                )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                        + ' Connection error, batch was not added to weaviate.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException(f"Create {data_object_type} in batch", response)

    def create_objects(self, objects_batch_request: ObjectsBatchRequest) -> list:
        """
        Creates multiple objects at once in weaviate

        Parameters
        ----------
        objects_batch_request : weaviate.batch.ObjectsBatchRequest
            The batch of objects that should be added.

        Returns
        -------
        list
            A list with the status of every object that was created.
        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not isinstance(objects_batch_request, ObjectsBatchRequest):
            raise TypeError(f"'reference_batch_request' should be of type \
                ObjectsBatchRequest but was given : {type(objects_batch_request)}")

        return self.create(
            batch_request=objects_batch_request
            )

    def create_references(self, reference_batch_request: ReferenceBatchRequest) -> list:
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
        list
            A list with the status of every reference added.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not isinstance(reference_batch_request, ReferenceBatchRequest):
            raise TypeError(f"'reference_batch_request' should be of type \
                ReferenceBatchRequest but was given : {type(reference_batch_request)}")

        return self.create(
            batch_request=reference_batch_request
            )

    def add_references(self, reference_batch_request: ReferenceBatchRequest) -> list:
        """
        'add_references' is deprecated, use 'create' or 'create_references' instead!
        """

        warnings.warn(
            "'add_references' is deprecated, use 'create' or 'create_references' instead!",
            DeprecationWarning
        )
        return self.create_references(
            reference_batch_request=reference_batch_request
            )
