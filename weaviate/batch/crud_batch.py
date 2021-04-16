import sys
from requests.exceptions import ReadTimeout
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
        Create data in batches, either Objects or References. This does NOT guarantee
        that each batch item (only Objects) is added/created. This can lead to a succesfull
        batch creation but unsucessfull per batch item creation. See the Examples below.

        Examples
        --------
        Add objects to the object batch.

        >>> batch = weaviate.ObjectsBatchRequest()
        >>> batch.add({}, 'NonExistingClass')
        >>> batch.add({}, 'ExistingClass')

        Note that 'NonExistingClass' is not present in the client's schema and 'ExistingObject'
        is present and has no proprieties.
        'batch.add' does not raise an exception because the objects added meet the required
        criteria (See the documentation of the 'weaviate.ObjectsBatchRequest.add' method for
        more information).

        >>> result = client.batch.create(batch)

        Successful batch creation even if one data object is inconsistent with the cleint's schema.
        We can find out more about what objects were succesfully created by analyzing the 'result'
        variable.

        >>> import json
        >>> print(json.dumps(result, indent=4))
        [
            {
                "class": "NonExistingClass",
                "creationTimeUnix": 1614852753747,
                "id": "154cbccd-89f4-4b29-9c1b-001a3339d89a",
                "properties": {},
                "deprecations": null,
                "result": {
                    "errors": {
                        "error": [
                            {
                                "message": "class 'NonExistingClass' not present in schema,
                                                        class NonExistingClass not present"
                            }
                        ]
                    }
                }
            },
            {
                "class": "ExistingClass",
                "creationTimeUnix": 1614852753746,
                "id": "b7b1cfbe-20da-496c-b932-008d35805f26",
                "properties": {},
                "vector": [
                    -0.05244319,
                    ...
                    0.076136276
                ],
                "deprecations": null,
                "result": {}
            }
        ]


        As it can be noticed the first object from the batch was not added/created, but the batch
        was succesfully created. The batch creation can be successful even if all the objects were
        NOT created. Check the status of the batch objects to find which object and why creation
        failed. Alternatively use 'Client().data_object.create' for Object creation that throw an
        error if data item is inconsistent or creation/addition failed.

        NOTE: The same is NOT true for ReferenceBatchRequest objects.

        Object that does not exist in weaviate.

        >>> object_1 = '154cbccd-89f4-4b29-9c1b-001a3339d89d'

        Objects that exist in weaviate.

        >>> object_2 = '154cbccd-89f4-4b29-9c1b-001a3339d89c'
        >>> object_3 = '254cbccd-89f4-4b29-9c1b-001a3339d89a'
        >>> object_4 = '254cbccd-89f4-4b29-9c1b-001a3339d89b'


        >>> batch = weaviate.ReferenceBatchRequest()
        >>> batch.add(object_1, 'NonExistingClass', 'existsWith', object_2)
        >>> batch.add(object_3, 'ExistingClass', 'existsWith', object_4)

        Both references were added to the batch request without error because they meet the
        required citeria (See the documentation of the 'weaviate.ReferenceBatchRequest.add' method
        for more information).

        >>> result = client.batch.create(batch)

        As it can be noticed the reference batch creation is successful (no error thrown). Now we
        can inspect the 'result'.

        >>> import json
        >>> print(json.dumps(client.batch.create(batch), indent=4))
        [
            {
                "from": "weaviate://localhost/NonExistingClass/
                                                154cbccd-89f4-4b29-9c1b-001a3339d89a/existsWith",
                "to": "weaviate://localhost/154cbccd-89f4-4b29-9c1b-001a3339d89b",
                "result": {
                    "status": "SUCCESS"
                }
            },
            {
                "from": "weaviate://localhost/ExistingClass/
                                                254cbccd-89f4-4b29-9c1b-001a3339d89a/existsWith",
                "to": "weaviate://localhost/254cbccd-89f4-4b29-9c1b-001a3339d89b",
                "result": {
                    "status": "SUCCESS"
                }
            }
        ]

        Both references were added successfully but one of them is corrupted (links two objects
        of unexisting class and one of the objects is not yet created).

        Adding References in batch is faster but it ignors validations like class name,
        property name and/or if both objects exist, resulting in a SUCESSFUL reference creation of
        unexisting object types and/or unexisting properties. If the consistency of the References
        is wanted use 'Client().data_object.reference.add' to have additional validation against
        the weaviate schema.

        Parameters
        ----------
        batch_request : weaviate.batch.BatchRequest
            Contains all the data objects that should be added in one batch.
            Note: Should be a sub-class of BatchRequest since BatchRequest
            is just an abstract class, e.g. ObjectsBatchRequest, ReferenceBatchRequest

        Returns
        -------
        list
            A list with the status of every data object added.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if isinstance(batch_request, ObjectsBatchRequest):
            data_object_type = "objects"
        elif isinstance(batch_request, ReferenceBatchRequest):
            data_object_type = "references"
        else:
            raise TypeError("Wrong argument type, expected a sub-class of BatchRequest "
                    "(ObjectsBatchRequest or ReferenceBatchRequest), got: " +\
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
        except ReadTimeout:
            message = (f"The {batch_request.__class__.__name__} was cancelled because it took "
                f"longer than the configured timeout of {self._connection.timeout_config[1]}s. "
                f"Try reducing the batch size (currently {len(batch_request)}) to a lower value. "
                "Aim to on average complete batch request within less than 10s")
            raise ReadTimeout(message) from None
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException(f"Create {data_object_type} in batch", response)

    def create_objects(self, objects_batch_request: ObjectsBatchRequest) -> list:
        """
        Creates multiple Objects at once in weaviate. This does not guarantee
        that each batch item is added/created. This can lead to a succesfull batch creation
        but unsucessfull per batch item creation. See the example bellow.

        Examples
        --------
        Add objects to the object batch.

        >>> batch = weaviate.ObjectsBatchRequest()
        >>> batch.add({}, 'NonExistingClass')
        >>> batch.add({}, 'ExistingClass')

        Note that 'NonExistingClass' is not present in the client's schema and 'ExistingObject'
        is present and has no proprieties.
        'batch.add' does not raise an exception because the objects added meet the required
        criteria (See the documentation of the 'weaviate.ObjectsBatchRequest.add' method for
        more information).

        >>> result = client.batch.create(batch)

        Successful batch creation even if one data object is inconsistent with the cleint's schema.
        We can find out more about what objects were succesfully created by analyzing the 'result'
        variable.

        >>> import json
        >>> print(json.dumps(result, indent=4))
        [
            {
                "class": "NonExistingClass",
                "creationTimeUnix": 1614852753747,
                "id": "154cbccd-89f4-4b29-9c1b-001a3339d89a",
                "properties": {},
                "deprecations": null,
                "result": {
                    "errors": {
                        "error": [
                            {
                                "message": "class 'NonExistingClass' not present in schema,
                                                            class NonExistingClass not present"
                            }
                        ]
                    }
                }
            },
            {
                "class": "ExistingClass",
                "creationTimeUnix": 1614852753746,
                "id": "b7b1cfbe-20da-496c-b932-008d35805f26",
                "properties": {},
                "vector": [
                    -0.05244319,
                    ...
                    0.076136276
                ],
                "deprecations": null,
                "result": {}
            }
        ]


        As it can be noticed the first object from the batch was not added/created, but the batch
        was succesfully created. The batch creation can be successful even if all the objects were
        NOT created. Check the status of the batch objects to find which object and why creation
        failed. Alternatively use 'Client().data_object.create' for Object creation that throw an
        error if data item is inconsistent or creation/addition failed.

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
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not isinstance(objects_batch_request, ObjectsBatchRequest):
            raise TypeError("'objects_batch_request' should be of type "
                f"ObjectsBatchRequest but was given : {type(objects_batch_request)}")

        return self.create(
            batch_request=objects_batch_request
            )

    def create_references(self, reference_batch_request: ReferenceBatchRequest) -> list:
        """
        Creates multiple References at once in weaviate.
        Adding References in batch is faster but it ignors validations like class name
        and property name, resulting in a SUCESSFUL reference creation of unexisting object
        types and/or unexisting properties. If the consistency of the References is wanted
        use 'Client().data_object.reference.add' to have additional validation against the
        weaviate schema. See Examples below.

        Examples
        --------
        Object that does not exist in weaviate.

        >>> object_1 = '154cbccd-89f4-4b29-9c1b-001a3339d89d'

        Objects that exist in weaviate.
        
        >>> object_2 = '154cbccd-89f4-4b29-9c1b-001a3339d89c'
        >>> object_3 = '254cbccd-89f4-4b29-9c1b-001a3339d89a'
        >>> object_4 = '254cbccd-89f4-4b29-9c1b-001a3339d89b'


        >>> batch = weaviate.ReferenceBatchRequest()
        >>> batch.add(object_1, 'NonExistingClass', 'existsWith', object_2)
        >>> batch.add(object_3, 'ExistingClass', 'existsWith', object_4)

        Both references were added to the batch request without error because they meet the
        required citeria (See the documentation of the 'weaviate.ReferenceBatchRequest.add' method
        for more information).

        >>> result = client.batch.create(batch)

        As it can be noticed the reference batch creation is successful (no error thrown). Now we
        can inspect the 'result'.

        >>> import json
        >>> print(json.dumps(client.batch.create(batch), indent=4))
        [
            {
                "from": "weaviate://localhost/NonExistingClass/
                                                154cbccd-89f4-4b29-9c1b-001a3339d89a/existsWith",
                "to": "weaviate://localhost/154cbccd-89f4-4b29-9c1b-001a3339d89b",
                "result": {
                    "status": "SUCCESS"
                }
            },
            {
                "from": "weaviate://localhost/ExistingClass/
                                                254cbccd-89f4-4b29-9c1b-001a3339d89a/existsWith",
                "to": "weaviate://localhost/254cbccd-89f4-4b29-9c1b-001a3339d89b",
                "result": {
                    "status": "SUCCESS"
                }
            }
        ]

        Both references were added successfully but one of them is corrupted (links two objects
        of unexisting class and one of the objects is not yet created).

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
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not isinstance(reference_batch_request, ReferenceBatchRequest):
            raise TypeError("'reference_batch_request' should be of type "
                f"ReferenceBatchRequest but was given : {type(reference_batch_request)}")

        return self.create(
            batch_request=reference_batch_request
            )
