"""
Batch class definitions.
"""
import sys
import time
from numbers import Real
from typing import Tuple, Callable, Optional, Sequence
from requests import ReadTimeout, Response
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.connect import Connection
from weaviate.util import _capitalize_first_letter
from .requests import BatchRequest, ObjectsBatchRequest, ReferenceBatchRequest

class Batch:
    """
    Batch class used to add multiple objects or object references at once into weaviate.
    To add data to the Batch use these methods of this class: `add_data_object` and
    `add_reference`. This object also stores 2 recommended batch size variables, one for objects
    and one for references. The recommended batch size is updated with every batch creation, and
    is the number of data objects/references that can be sent/processed by the Weaviate server in
    `creation_time` interval (see `configure` or `__call__` method on how to set this value, by
    default it is set to 10). The initial value is None/batch_size and is updated with every batch
    create methods. The values can be accessed with the getters: `recommended_num_objects` and
    `recommended_num_references`.
    NOTE: If the UUID of one of the objects already exists then the existing object will be
    replaced by the new object.

    This class can be used in 3 ways:

    Case I:
        Everything should be done by the user, i.e. the user should add the
        objects/object-references and create them whenever the user wants. To create one of the
        data type use these methods of this class: `create_objects`, `create_references` and
        `flush`. This case has the Batch instance's batch_size set to None (see docs for the
        `configure` or `__call__` method). Can be used in a context manager, see below.

    Case II:
        Batch auto-creates when full. This can be achieved by setting the Batch instance's
        batch_size set to a positive integer (see docs for the `configure` or `__call__` method).
        The batch_size in this case corresponds to the sum of added objects and references.
        This case does not require the user to create the batch/s, but it can be done. Also to
        create non-full batches (last batche/s) that do not meet the requirement to be auto-created
        use the `flush` method. Can be used in a context manager, see below.

    Case III:
        Similar to Case II but uses dynamic batching, i.e. auto-creates either objects or
        references when one of them reached the `recommended_num_objects` or
        `recommended_num_references` respectively. See docs for the `configure` or `__call__`
        method for how to enable it.

    Context-manager support: Can be use with the `with` statement. When it exists the context-
        manager it calls the `flush` method for you. Can be combined with `configure`/`__call__`
        method, in order to set it to the desired Case.

    Examples
    --------
    Here are examples for each CASE described above. Here `client` is an instance of the
    `weaviate.Client`.

    >>> object_1 = '154cbccd-89f4-4b29-9c1b-001a3339d89d'
    >>> object_2 = '154cbccd-89f4-4b29-9c1b-001a3339d89c'
    >>> object_3 = '254cbccd-89f4-4b29-9c1b-001a3339d89a'
    >>> object_4 = '254cbccd-89f4-4b29-9c1b-001a3339d89b'

    For Case I:

    >>> client.batch.shape
    (0, 0)
    >>> client.batch.add_data_object({}, 'MyClass')
    >>> client.batch.add_data_object({}, 'MyClass')
    >>> client.batch.add_reference(object_1, 'MyClass', 'myProp', object_2)
    >>> client.batch.shape
    (2, 1)
    >>> client.batch.create_objects()
    >>> client.batch.shape
    (0, 1)
    >>> client.batch.create_references()
    >>> client.batch.shape
    (0, 0)
    >>> client.batch.add_data_object({}, 'MyClass')
    >>> client.batch.add_reference(object_3, 'MyClass', 'myProp', object_4)
    >>> client.batch.shape
    (1, 1)
    >>> client.batch.flush()
    >>> client.batch.shape
    (0, 0)

    Or with a context manager:

    >>> with client.batch as batch:
    ...     batch.add_data_object({}, 'MyClass')
    ...     batch.add_reference(object_3, 'MyClass', 'myProp', object_4)
    >>> # flush was called
    >>> client.batch.shape
    (0, 0)

    For Case II:

    >>> client.batch(batch_size=3)
    >>> client.batch.shape
    (0, 0)
    >>> client.batch.add_data_object({}, 'MyClass')
    >>> client.batch.add_reference(object_1, 'MyClass', 'myProp', object_2)
    >>> client.batch.shape
    (1, 1)
    >>> client.batch.add_data_object({}, 'MyClass') # sum of data_objects and references reached
    >>> client.batch.shape
    (0, 0)

    Or with a context manager and `__call__` method:

    >>> with client.batch(batch_size=3) as batch:
    ...     batch.add_data_object({}, 'MyClass')
    ...     batch.add_reference(object_3, 'MyClass', 'myProp', object_4)
    ...     batch.add_data_object({}, 'MyClass')
    ...     batch.add_reference(object_1, 'MyClass', 'myProp', object_4)
    >>> # flush was called
    >>> client.batch.shape
    (0, 0)

    Or with a context manager and setter:

    >>> client.batch.batch_size = 3
    >>> with client.batch as batch:
    ...     batch.add_data_object({}, 'MyClass')
    ...     batch.add_reference(object_3, 'MyClass', 'myProp', object_4)
    ...     batch.add_data_object({}, 'MyClass')
    ...     batch.add_reference(object_1, 'MyClass', 'myProp', object_4)
    >>> # flush was called
    >>> client.batch.shape
    (0, 0)

    For Case III:
    Same as Case II but you need to configure or enable 'dynamic' batching.

    >>> client.batch.configure(batch_size=3, dynamic=True) # 'batch_size' must be an valid int

    Or:

    >>> client.batch.batch_size = 3
    >>> client.batch.dynamic = True

    See the documentation of the `configure`( or `__call__`) and the setters for more information
    on how/why and what you need to configure/set in order to use a particular Case.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Batch class instance. This defaults to manual creation configuration.
        See docs for the `configure` or `__call__` method for different types of configurations.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        # set all protected attributes
        self._connection = connection
        self._objects_batch = ObjectsBatchRequest()
        self._reference_batch = ReferenceBatchRequest()

        ## user configurable, need to be public should implement a setter/getter
        self._recommended_num_objects = None
        self._recommended_num_references = None
        self._callback = None
        self._batch_size = None
        self._creation_time = 10.0
        self._timeout_retries = 0
        self._batching_type = None

    def configure(self,
            batch_size: Optional[int]=None,
            creation_time: Real=10,
            timeout_retries: int=0,
            callback: Optional[Callable[[dict], None]]=None,
            dynamic: bool=False
        ) -> 'Batch':
        """
        Configure the instance to your needs. (`__call__` and `configure` methods are the same).
        NOTE: It has default values and if you want to change only one use a setter instead, or
        provide all the configurations.

        Parameters
        ----------
        batch_size : Optional[int], optional
            The batch size to be use. This value sets the Batch functionality, if `batch_size` is
            None then no auto-creation is done (`callback` and `dynamic` are ignored). If it is a
            positive number auto-creation is enabled and the value represents: 1) in case `dynamic`
            is False -> the number of data in the Batch (sum of objects and references) when to
            auto-create; 2) in case `dynamic` is True -> the initial value for both
            `recommended_num_objects` and `recommended_num_references`, by default None
        creation_time : Real, optional
            The time interval it should take the Batch to be created, used ONLY for computing
            `recommended_num_objects` and `recommended_num_references`, by default 10
        timeout_retries : int, optional
            Number of times to retry to create a Batch that failed with TimeOut error, by default 0
        callback : Optional[Callable[[dict], None]], optional
            A callback function on the results of each (objects and references) batch types. It is
            used only when `batch_size` is NOT None, by default None
        dynamic : bool, optional
            Whether to use dynamic batching or not, by default False

        Returns
        -------
        Batch
            Updated self.

        Raises
        ------
        TypeError
            If one of the arguments is of a wrong type.
        ValueError
            If the value of one of the arguments is wrong.
        """

        return self.__call__(
            batch_size=batch_size,
            creation_time=creation_time,
            timeout_retries=timeout_retries,
            callback=callback,
            dynamic=dynamic,
        )

    def __call__(self,
            batch_size: Optional[int]=None,
            creation_time: Real=10,
            timeout_retries: int=0,
            callback: Optional[Callable[[dict], None]]=None,
            dynamic: bool=False
        ) -> 'Batch':
        """
        Configure the instance to your needs. (`__call__` and `configure` methods are the same).
        NOTE: It has default values and if you want to change only one use a setter instead, or
        provide all the configurations.

        Parameters
        ----------
        batch_size : Optional[int], optional
            The batch size to be use. This value sets the Batch functionality, if `batch_size` is
            None then no auto-creation is done (`callback` and `dynamic` are ignored). If it is a
            positive number auto-creation is enabled and the value represents: 1) in case `dynamic`
            is False -> the number of data in the Batch (sum of objects and references) when to
            auto-create; 2) in case `dynamic` is True -> the initial value for both
            `recommended_num_objects` and `recommended_num_references`, by default None
        creation_time : Real, optional
            The time interval it should take the Batch to be created, used ONLY for computing
            `recommended_num_objects` and `recommended_num_references`, by default 10
        timeout_retries : int, optional
            Number of times to retry to create a Batch that failed with TimeOut error, by default 0
        callback : Optional[Callable[[dict], None]], optional
            A callback function on the results of each (objects and references) batch types. It is
            used only when `batch_size` is NOT None, by default None
        dynamic : bool, optional
            Whether to use dynamic batching or not, by default False

        Returns
        -------
        Batch
            Updated self.

        Raises
        ------
        TypeError
            If one of the arguments is of a wrong type.
        ValueError
            If the value of one of the arguments is wrong.
        """

        _check_positive_num(creation_time, 'creation_time', Real)
        _check_non_negative(timeout_retries, 'timeout_retries', int)

        # set Batch to manual import
        if batch_size is None:
            self._callback = None
            self._batch_size = None
            self._creation_time = creation_time
            self._timeout_retries = timeout_retries
            self._batching_type = None
            return self

        _check_positive_num(batch_size, 'batch_size', int)
        _check_bool(dynamic, 'dynamic')

        self._callback = callback
        self._batch_size = batch_size
        self._creation_time = creation_time
        self._timeout_retries = timeout_retries

        if dynamic is False: # set Batch to auto-commit with fixed batch_size
            self._batching_type = 'fixed'
        else: # else set to 'dynamic'
            self._batching_type = 'dynamic'
            self._recommended_num_objects = batch_size
            self._recommended_num_references = batch_size
        self._auto_create()
        return self

    def add_data_object(self,
            data_object: dict,
            class_name: str,
            uuid: Optional[str]=None,
            vector: Optional[Sequence]=None
        ) -> None:
        """
        Add one object to this batch.
        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Parameters
        ----------
        data_object : dict
            Object to be added as a dict datatype.
        class_name : str
            The name of the class this object belongs to.
        uuid : str, optional
            UUID of the object as a string, by default None
        vector: Sequence, optional
            The embedding of the object that should be created. Used only class objects that do not
            have a vectorization module. Supported types are `list`, 'numpy.ndarray`,
            `torch.Tensor` and `tf.Tensor`,
            by default None.

        Raises
        ------
        TypeError
            If an argument passed is not of an appropriate type.
        ValueError
            If 'uuid' is not of a propper form.
        """

        self._objects_batch.add(
            class_name=_capitalize_first_letter(class_name),
            data_object=data_object,
            uuid=uuid,
            vector=vector,
        )

        if self._batching_type:
            self._auto_create()

    def add_reference(self,
            from_object_uuid: str,
            from_object_class_name: str,
            from_property_name: str,
            to_object_uuid: str
        ) -> None:
        """
        Add one reference to this batch.

        Parameters
        ----------
        from_object_uuid : str
            The UUID or URL of the object that should reference another object.
        from_object_class_name : str
            The name of the class that should reference another object.
        from_property_name : str
            The name of the property that contains the reference.
        to_object_uuid : str
            The UUID or URL of the object that is actually referenced.

        Raises
        ------
        TypeError
            If arguments are not of type str.
        ValueError
            If 'uuid' is not valid or cannot be extracted.
        """

        self._reference_batch.add(
            from_object_class_name=_capitalize_first_letter(from_object_class_name),
            from_object_uuid=from_object_uuid,
            from_property_name=from_property_name,
            to_object_uuid=to_object_uuid,
        )

        if self._batching_type:
            self._auto_create()

    def _create_data(self,
            data_type: str,
            batch_request: BatchRequest,
        ) -> Response:
        """
        Create data in batches, either Objects or References. This does NOT guarantee
        that each batch item (only Objects) is added/created. This can lead to a successfull
        batch creation but unsuccessfull per batch item creation. See the Examples below.

        Parameters
        ----------
        data_type : str
            The data type of the BatchRequest, used to save time for not checking the type of the
            BatchRequest.
        batch_request : weaviate.batch.BatchRequest
            Contains all the data objects that should be added in one batch.
            Note: Should be a sub-class of BatchRequest since BatchRequest
            is just an abstract class, e.g. ObjectsBatchRequest, ReferenceBatchRequest

        Returns
        -------
        requests.Response
            The requests response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        try:
            for i in range(self._timeout_retries + 1):
                try:
                    response = self._connection.post(
                        path='/batch/' + data_type,
                        weaviate_object=batch_request.get_request_body()
                    )
                except ReadTimeout:
                    if i == self._timeout_retries:
                        raise
                    print('[ERROR] Batch ReadTimeout Exception occurred! Retring in 1s. '
                        f'[{i+1}/{self._timeout_retries}]', file=sys.stderr)
                    time.sleep(1)
                else:
                    break
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Batch was not added to weaviate.') from conn_err
        except ReadTimeout:
            message = (
                f"The '{data_type}' creation was cancelled because it took "
                f"longer than the configured timeout of {self._connection.timeout_config[1]}s. "
                f"Try reducing the batch size (currently {len(batch_request)}) to a lower value. "
                "Aim to on average complete batch request within less than 10s"
            )
            raise ReadTimeout(message) from None
        if response.status_code == 200:
            return response
        raise UnexpectedStatusCodeException(f"Create {data_type} in batch", response)

    def create_objects(self) -> list:
        """
        Creates multiple Objects at once in Weaviate. This does not guarantee that each batch item
        is added/created to the Weaviate server. This can lead to a successfull batch creation but
        unsuccessfull per batch item creation. See the example bellow.
        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Examples
        --------
        Here `client` is an instance of the `weaviate.Client`.

        Add objects to the object batch.

        >>> client.batch.add_data_object({}, 'NonExistingClass')
        >>> client.batch.add_data_object({}, 'ExistingClass')

        Note that 'NonExistingClass' is not present in the client's schema and 'ExistingObject'
        is present and has no proprieties. 'client.batch.add_data_object' does not raise an
        exception because the objects added meet the required criteria (See the documentation of
        the 'weaviate.Batch.add_data_object' method for more information).

        >>> result = client.batch.create_objects(batch)

        Successful batch creation even if one data object is inconsistent with the client's schema.
        We can find out more about what objects were successfully created by analyzing the 'result'
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
        was successfully created. The batch creation can be successful even if all the objects were
        NOT created. Check the status of the batch objects to find which object and why creation
        failed. Alternatively use 'client.data_object.create' for Object creation that throw an
        error if data item is inconsistent or creation/addition failed.

        To check the results of batch creation when using the auto-creation Batch, use a 'callback'
        (see the docs `configure` or `__call__` method for more information).

        Returns
        -------
        list
            A list with the status of every object that was created.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if len(self._objects_batch) != 0:
            response = self._create_data(
                data_type='objects',
                batch_request=self._objects_batch,
            )
            obj_per_second = len(self._objects_batch) / response.elapsed.total_seconds()
            self._recommended_num_objects = round(obj_per_second * self._creation_time)
            self._objects_batch = ObjectsBatchRequest()
            return response.json()
        return []

    def create_references(self) -> list:
        """
        Creates multiple References at once in Weaviate.
        Adding References in batch is faster but it ignors validations like class name
        and property name, resulting in a SUCCESSFUL reference creation of a nonexistent object
        types and/or a nonexistent properties. If the consistency of the References is wanted
        use 'client.data_object.reference.add' to have additional validation against the
        weaviate schema. See Examples below.

        Examples
        --------
        Here `client` is an instance of the `weaviate.Client`.

        Object that does not exist in weaviate.

        >>> object_1 = '154cbccd-89f4-4b29-9c1b-001a3339d89d'

        Objects that exist in weaviate.

        >>> object_2 = '154cbccd-89f4-4b29-9c1b-001a3339d89c'
        >>> object_3 = '254cbccd-89f4-4b29-9c1b-001a3339d89a'
        >>> object_4 = '254cbccd-89f4-4b29-9c1b-001a3339d89b'

        >>> client.batch.add_reference(object_1, 'NonExistingClass', 'existsWith', object_2)
        >>> client.batch.add_reference(object_3, 'ExistingClass', 'existsWith', object_4)

        Both references were added to the batch request without error because they meet the
        required citeria (See the documentation of the 'weaviate.Batch.add_reference' method
        for more information).

        >>> result = client.batch.create_references()

        As it can be noticed the reference batch creation is successful (no error thrown). Now we
        can inspect the 'result'.

        >>> import json
        >>> print(result, indent=4))
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
        of nonexisting class and one of the objects is not yet created). To make use of the
        validation, crete each references individually (see the client.data_object.reference.add
        method).

        Returns
        -------
        list
            A list with the status of every reference added.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if len(self._reference_batch) != 0:
            response = self._create_data(
                data_type='references',
                batch_request=self._reference_batch,
            )
            ref_per_second = len(self._reference_batch) / response.elapsed.total_seconds()
            self._recommended_num_references = round(ref_per_second * self._creation_time)
            self._reference_batch = ReferenceBatchRequest()
            return response.json()
        return []

    def _auto_create(self) -> None:
        """
        Auto create both objects and references in the batch. This protected method works with a
        fixed batch size and with dynamic batching. FOr a 'fixed' batching type it auto-creates
        when the sum of both objects and references equals batch_size. For dynamic batching it
        creates both batch requests when only one is full.
        """

        # greater or equal in case the self._batch_size is changed manually
        if self._batching_type == 'fixed':
            if sum(self.shape) >= self._batch_size:
                self.flush()
            return
        if self._batching_type == 'dynamic':
            if (
                self.num_objects() >= self._recommended_num_objects
                or self.num_references() >= self._recommended_num_references
            ):
                self.flush()
            return
        # just in case
        raise ValueError(f'Unsupported batching type "{self._batching_type}"')

    def flush(self) -> None:
        """
        Flush both objects and references to the Weaviate server and call the callback function
        if one is provided. (See the docs for `configure` or `__call__` for how to set one.)
        """

        result_objects = self.create_objects()
        result_references = self.create_references()
        if self._callback is not None:
            if result_objects:
                self._callback(result_objects)
            if result_references:
                self._callback(result_references)

    def num_objects(self) -> int:
        """
        Get current number of objects in the batch.

        Returns
        -------
        int
            The number of objects in the batch.
        """

        return len(self._objects_batch)

    def num_references(self) -> int:
        """
        Get current number of references in the batch.

        Returns
        -------
        int
            The number of references in the batch.
        """

        return len(self._reference_batch)

    def pop_object(self, index: int=-1) -> dict:
        """
        Remove and return the object at index (default last).

        Parameters
        ----------
        index : int, optional
            The index of the object to pop, by default -1 (last item).

        Returns
        -------
        dict
            The popped object.

        Raises
        -------
        IndexError
            If batch is empty or index is out of range.
        """

        return self._objects_batch.pop(index)

    def pop_reference(self, index: int=-1) -> dict:
        """
        Remove and return the reference at index (default last).

        Parameters
        ----------
        index : int, optional
            The index of the reference to pop, by default -1 (last item).

        Returns
        -------
        dict
            The popped reference.

        Raises
        -------
        IndexError
            If batch is empty or index is out of range.
        """

        return self._reference_batch.pop(index)

    def empty_objects(self) -> None:
        """
        Remove all the objects from the batch.
        """

        self._objects_batch.empty()

    def empty_references(self) -> None:
        """
        Remove all the references from the batch.
        """

        self._reference_batch.empty()

    def is_empty_objects(self) -> bool:
        """
        Check if batch contains any objects.

        Returns
        -------
        bool
            Whether the Batch object list is empty.
        """

        return self._objects_batch.is_empty()

    def is_empty_references(self) -> bool:
        """
        Check if batch contains any references.

        Returns
        -------
        bool
            Whether the Batch reference list is empty.
        """

        return self._reference_batch.is_empty()

    @property
    def shape(self) -> Tuple[int, int]:
        """
        Get current number of objects and references in the batch.

        Returns
        -------
        Tuple[int, int]
            The number of objects and references, respectively, in the batch as a tuple,
            i.e. returns (number of objects, number of references).
        """

        return (len(self._objects_batch), len(self._reference_batch))

    @property
    def batch_size(self) -> Optional[int]:
        """
        Setter and Getter for `batch_size`.

        Parameters
        ----------
        value : Optional[int]
            Setter ONLY: The new value for the batch_size. If NOT None it will try to auto-create
            the existing data if it meets the requirements. If previous value was None then it will
            be set to new value and will change the batching type to auto-create with dynamic set
            to False. See the documentation for `configure` or `__call__` for more info.
            If recommended_num_objects is None then it is initialized with the new value of the
            batch_size (same for references).

        Returns
        -------
        Optional[int]
            Getter ONLY: The current value of the batch_size. It is NOT the current number of
            data in the Batch. See the documentation for `configure` or `__call__` for more info.

        Raises
        ------
        TypeError
            Setter ONLY: If the new value is not of type int.
        ValueError
            Setter ONLY: If the new value has a non positive value.
        """

        return self._batch_size

    @batch_size.setter
    def batch_size(self, value: Optional[int]) -> None:

        if value is None:
            self._batch_size = None
            self._batching_type = None
            return

        _check_positive_num(value, 'batch_size', int)
        self._batch_size = value
        if self._batching_type is None:
            self._batching_type = 'fixed'
        if self._recommended_num_objects is None:
            self._recommended_num_objects = value
        if self._recommended_num_references is None:
            self._recommended_num_references = value
        self._auto_create()

    @property
    def dynamic(self) -> bool:
        """
        Setter and Getter for `dynamic`.

        Parameters
        ----------
        value : bool
            Setter ONLY: En/dis-able the dynamic batching. If batch_size is None the value is not
            set, otherwise it will set the dynamic to new value and auto-create if it meets the
            requirements.

        Returns
        -------
        bool
            Getter ONLY: Wether the dynamic batching is enabled.

        Raises
        ------
        TypeError
            Setter ONLY: If the new value is not of type bool.
        """

        return self._batching_type == 'dynamic'

    @dynamic.setter
    def dynamic(self, value: bool) -> None:

        if self._batching_type is None:
            return

        _check_bool(value, 'dynamic')

        if value is True:
            self._batching_type = 'dynamic'
        else:
            self._batching_type = 'fixed'
        self._auto_create()

    @property
    def recommended_num_objects(self) -> Optional[int]:
        """
        The recommended number of objects per batch. If None then it could not be computed.

        Returns
        -------
        Optional[int]
            The recommended number of objects per batch. If None then it could not be computed.
        """

        return self._recommended_num_objects

    @property
    def recommended_num_references(self) -> Optional[int]:
        """
        The recommended number of references per batch. If None then it could not be computed.

        Returns
        -------
        Optional[int]
            The recommended number of references per batch. If None then it could not be computed.
        """

        return self._recommended_num_references

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()

    @property
    def creation_time(self) -> Real:
        """
        Setter and Getter for `creation_time`.

        Parameters
        ----------
        value : Real
            Setter ONLY: Set new value to creation_time. The recommended_num_objects/references
            values are updated to this new value. If the batch_size is not None it will auto-create
            the batch if the requirements are met.

        Returns
        -------
        Real
            Getter ONLY: The `creation_time` value.

        Raises
        ------
        TypeError
            Setter ONLY: If the new value is not of type Real.
        ValueError
            Setter ONLY: If the new value has a non positive value.
        """

        return self._creation_time

    @creation_time.setter
    def creation_time(self, value: Real) -> None:

        _check_positive_num(value, 'creation_time', Real)
        if self._recommended_num_references is not None:
            self._recommended_num_references = round(
                self._recommended_num_references * value / self._creation_time
            )
        if self._recommended_num_objects is not None:
            self._recommended_num_objects = round(
                self._recommended_num_objects * value / self._creation_time
            )
        self._creation_time = value
        if self._batching_type:
            self._auto_create()

    @property
    def timeout_retries(self) -> int:
        """
        Setter and Getter for `timeout_retries`.

        Propreties
        ----------
        value : int
            Setter ONLY: The new value for `timeout_retries`.

        Returns
        -------
        int
            Getter ONLY: The `timeout_retries` value.

        Raises
        ------
        TypeError
            Setter ONLY: If the new value is not of type int.
        ValueError
            Setter ONLY: If the new value has a non positive value.
        """

        return self._timeout_retries

    @timeout_retries.setter
    def timeout_retries(self, value: int) -> None:

        _check_non_negative(value, 'timeout_retries', int)
        self._timeout_retries = value


def _check_positive_num(value: Real, arg_name: str, data_type: type) -> None:
    """
    Check if the `value` of the `arg_name` is a positive number.

    Parameters
    ----------
    value : Union[int, float]
        The value to check.
    arg_name : str
        The name of the variable from the original function call. Used for error message.
    data_type : type
        The data type to check for.

    Raises
    ------
    TypeError
        If the `value` is not of type `data_type`.
    ValueError
        If the `value` has a non positive value.
    """

    if not isinstance(value, data_type) or isinstance(value, bool):
        raise TypeError(f"'{arg_name}' must be of type {data_type}.")
    if value <= 0:
        raise ValueError(f"'{arg_name}' must be positive, i.e. greater that zero (>0).")


def _check_non_negative(value: Real, arg_name: str, data_type: type) -> None:
    """
    Check if the `value` of the `arg_name` is a non-negative number.

    Parameters
    ----------
    value : Union[int, float]
        The value to check.
    arg_name : str
        The name of the variable from the original function call. Used for error message.
    data_type : type
        The data type to check for.

    Raises
    ------
    TypeError
        If the `value` is not of type `data_type`.
    ValueError
        If the `value` has a negative value.
    """

    if not isinstance(value, data_type) or isinstance(value, bool):
        raise TypeError(f"'{arg_name}' must be of type {data_type}.")
    if value < 0:
        raise ValueError(f"'{arg_name}' must be positive, i.e. greater or equal that zero (>=0).")


def _check_bool(value: bool, arg_name: str) -> None:
    """
    Check if bool.

    Parameters
    ----------
    value : bool
        The value to check.
    arg_name : str
        The name of the variable from the original function call. Used for error message.

    Raises
    ------
    TypeError
        If the `value` is not of type bool.
    """

    if not isinstance(value, bool):
        raise TypeError(f"'{arg_name}' must be of type bool.")
