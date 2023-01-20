"""
Batch class definitions.
"""
import sys
import threading
import time
import warnings
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from numbers import Real
import uuid
from typing import Tuple, Callable, Optional, Sequence, Union, List


from requests import ReadTimeout, Response
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from .requests import BatchRequest, ObjectsBatchRequest, ReferenceBatchRequest, BatchResponse
from ..error_msgs import (
    BATCH_REF_DEPRECATION_NEW_V14_CLS_NS_W,
    BATCH_REF_DEPRECATION_OLD_V14_CLS_NS_W,
    BATCH_EXECUTOR_SHUTDOWN_W,
)
from ..exceptions import UnexpectedStatusCodeException
from ..util import (
    _capitalize_first_letter,
    check_batch_result,
    _check_positive_num,
)
from ..warnings import _Warnings

BatchRequestType = Union[ObjectsBatchRequest, ReferenceBatchRequest]


@dataclass()
class WeaviateErrorRetryConf:
    """Configures how often objects should be retried when Weavaite returns an error and which errors should be included
    or excluded.
    By default, all errors are retried.

    Parameters
    ----------
    number_retries: int
       How often a batch that includes objects with errors should be retried. Must be >=1.
    errors_to_exclude: Optional[List[str]]
        Which errors should NOT be retried. All other errors will be retried. An object will be skipped, when the given
        string is part of the weaviate error message.

        Example: errors_to_exclude =["string1", "string2"] will match the error with message "Long error message that
        contains string1".
    errors_to_include: Optional[List[str]]
        Which errors should be retried. All other errors will NOT be retried. An object will be included, when the given
        string is part of the weaviate error message.

        Example: errors_to_include =["string1", "string2"] will match the error with message "Long error message that
        contains string1".
    """

    number_retries: int = 3
    errors_to_exclude: Optional[List[str]] = None
    errors_to_include: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.errors_to_exclude is not None and self.errors_to_include is not None:
            raise ValueError(self.__module__ + " can either include or exclude errors")

        _check_positive_num(self.number_retries, "number_retries", int)

        def check_lists(error_list: Optional[List[str]]) -> None:
            if error_list is None:
                return
            if any(not isinstance(entry, str) for entry in error_list):
                raise ValueError("List entries must be strings.")

        check_lists(self.errors_to_exclude)
        check_lists(self.errors_to_include)

        if self.errors_to_include is not None and len(self.errors_to_include) == 0:
            raise ValueError("errors_to_include has 0 entries and no error will be retried.")


UUID = Union[str, uuid.UUID]


class BatchExecutor(ThreadPoolExecutor):
    """
    Weaviate Batch Executor to run batch requests in separate thread.
    This class implements an additional method `is_shutdown` that us used my the context manager.
    """

    def is_shutdown(self) -> bool:
        """
        Check if executor is shutdown.

        Returns
        -------
        bool
            Whether the BatchExecutor is shutdown.
        """

        return self._shutdown


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
        create non-full batches (last batch/es) that do not meet the requirement to be auto-created
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
        # do not keep too many past values, so it is a better estimation of the throughput is computed for 1 second
        self._objects_throughput_frame = deque(maxlen=5)
        self._references_throughput_frame = deque(maxlen=5)
        self._future_pool = []
        self._reference_batch_queue = []
        self._callback_lock = threading.Lock()

        # user configurable, need to be public should implement a setter/getter
        self._recommended_num_objects = None
        self._recommended_num_references = None
        self._callback: Optional[Callable[[BatchResponse], None]] = check_batch_result
        self._weaviate_error_retry: Optional[WeaviateErrorRetryConf] = None
        self._batch_size = None
        self._creation_time = min(self._connection.timeout_config[1] / 10, 2)
        self._timeout_retries = 3
        self._connection_error_retries = 3
        self._batching_type = None
        self._num_workers = 1

        # thread pool executor
        self._executor: Optional[BatchExecutor] = None

    def configure(
        self,
        batch_size: Optional[int] = None,
        creation_time: Optional[Real] = None,
        timeout_retries: int = 3,
        connection_error_retries: int = 3,
        weaviate_error_retries: Optional[WeaviateErrorRetryConf] = None,
        callback: Optional[Callable[[dict], None]] = check_batch_result,
        dynamic: bool = False,
        num_workers: int = 1,
    ) -> "Batch":
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
            How long it should take to create a Batch. Used ONLY for computing dynamic batch sizes. By default None
        timeout_retries : int, optional
            Number of retries to create a Batch that failed with ReadTimeout, by default 3
        weaviate_error_retries: Optional[WeaviateErrorRetryConf], by default None
            How often batch-elements with an error originating from weaviate (for example transformer timeouts) should
            be retried and which errors should be ignored and/or included. See documentation for WeaviateErrorRetryConf
            for details.
        connection_error_retries : int, optional
            Number of retries to create a Batch that failed with ConnectionError, by default 3
        callback : Optional[Callable[[dict], None]], optional
            A callback function on the results of each (objects and references) batch types.
            By default `weaviate.util.check_batch_result`.
        dynamic : bool, optional
            Whether to use dynamic batching or not, by default False
        num_workers : int, optional
            The maximal number of concurrent threads to run batch import. Only used for non-MANUAL
            batching. i.e. is used only with AUTO or DYNAMIC batching.
            By default, the multi-threading is disabled. Use with care to not overload your weaviate instance.

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
            weaviate_error_retries=weaviate_error_retries,
            connection_error_retries=connection_error_retries,
            callback=callback,
            dynamic=dynamic,
            num_workers=num_workers,
        )

    def __call__(
        self,
        batch_size: Optional[int] = None,
        creation_time: Optional[Real] = None,
        timeout_retries: int = 3,
        connection_error_retries: int = 3,
        weaviate_error_retries: Optional[WeaviateErrorRetryConf] = None,
        callback: Optional[Callable[[dict], None]] = check_batch_result,
        dynamic: bool = False,
        num_workers: int = 1,
    ) -> "Batch":
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
            How long it should take to create a Batch. Used ONLY for computing dynamic batch sizes. By default None
        timeout_retries : int, optional
            Number of retries to create a Batch that failed with ReadTimeout, by default 3
        connection_error_retries : int, optional
            Number of retries to create a Batch that failed with ConnectionError, by default 3
        weaviate_error_retries: WeaviateErrorRetryConf, Optional
            How often batch-elements with an error originating from weaviate (for example transformer timeouts) should
            be retried and which errors should be ignored and/or included. See documentation for WeaviateErrorRetryConf
            for details.
        callback : Optional[Callable[[dict], None]], optional
            A callback function on the results of each (objects and references) batch types.
            By default `weaviate.util.check_batch_result`
        dynamic : bool, optional
            Whether to use dynamic batching or not, by default False
        num_workers : int, optional
            The maximal number of concurrent threads to run batch import. Only used for non-MANUAL
            batching. i.e. is used only with AUTO or DYNAMIC batching.
            By default, the multi-threading is disabled. Use with care to not overload your weaviate instance.

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
        if creation_time is not None:
            _check_positive_num(creation_time, "creation_time", Real)
            self._creation_time = creation_time
        else:
            self._creation_time = min(self._connection.timeout_config[1] / 10, 2)

        _check_non_negative(timeout_retries, "timeout_retries", int)
        _check_non_negative(connection_error_retries, "connection_error_retries", int)
        _check_non_negative(connection_error_retries, "weaviate_error_retries", int)

        self._callback = callback

        self._timeout_retries = timeout_retries
        self._connection_error_retries = connection_error_retries
        self._weaviate_error_retry = weaviate_error_retries
        # set Batch to manual import
        if batch_size is None:
            self._batch_size = None
            self._batching_type = None
            return self

        _check_positive_num(batch_size, "batch_size", int)
        _check_positive_num(num_workers, "num_workers", int)
        _check_bool(dynamic, "dynamic")

        self._batch_size = batch_size
        if dynamic is False:  # set Batch to auto-commit with fixed batch_size
            self._batching_type = "fixed"
        else:  # else set to 'dynamic'
            self._batching_type = "dynamic"
            self._recommended_num_objects = batch_size
            self._recommended_num_references = batch_size

        if self._num_workers != num_workers:
            self.flush()
            self.shutdown()
            self._num_workers = num_workers
            self.start()

        self._auto_create()
        return self

    def add_data_object(
        self,
        data_object: dict,
        class_name: str,
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
    ) -> str:
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
        uuid : Optional[UUID], optional
            The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
            If it is None an UUIDv4 will generated, by default None
        vector: Sequence or None, optional
            The embedding of the object that should be validated.
            Can be used when:
             - a class does not have a vectorization module.
             - The given vector was generated using the _identical_ vectorization module that is configured for the
             class. In this case this vector takes precedence.

            Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`,
            by default None.

        Returns
        -------
        str
            The UUID of the added object. If one was not provided a UUIDv4 will be generated.

        Raises
        ------
        TypeError
            If an argument passed is not of an appropriate type.
        ValueError
            If 'uuid' is not of a proper form.
        """
        uuid = self._objects_batch.add(
            class_name=_capitalize_first_letter(class_name),
            data_object=data_object,
            uuid=uuid,
            vector=vector,
        )

        if self._batching_type:
            self._auto_create()

        return uuid

    def add_reference(
        self,
        from_object_uuid: UUID,
        from_object_class_name: str,
        from_property_name: str,
        to_object_uuid: UUID,
        to_object_class_name: Optional[str] = None,
    ) -> None:
        """
        Add one reference to this batch.

        Parameters
        ----------
        from_object_uuid : UUID
            The UUID of the object, as an uuid.UUID object or str, that should reference another object.
            It can be a Weaviate beacon or Weaviate href.
        from_object_class_name : str
            The name of the class that should reference another object.
        from_property_name : str
            The name of the property that contains the reference.
        to_object_uuid : UUID
            The UUID of the object, as an uuid.UUID object or str, that is actually referenced.
            It can be a Weaviate beacon or Weaviate href.
        to_object_class_name : Optional[str], optional
            The referenced object class name to which to add the reference (with UUID
            `to_object_uuid`), it is included in Weaviate 1.14.0, where all objects are namespaced
            by class name.
            STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
            versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < v1.14.0,
            by default None

        Raises
        ------
        TypeError
            If arguments are not of type str.
        ValueError
            If 'uuid' is not valid or cannot be extracted.
        """

        is_server_version_14 = self._connection.server_version >= "1.14"

        if to_object_class_name is None and is_server_version_14:
            warnings.warn(
                message=BATCH_REF_DEPRECATION_NEW_V14_CLS_NS_W,
                category=DeprecationWarning,
                stacklevel=1,
            )
        if to_object_class_name is not None:
            if not is_server_version_14:
                warnings.warn(
                    message=BATCH_REF_DEPRECATION_OLD_V14_CLS_NS_W,
                    category=DeprecationWarning,
                    stacklevel=1,
                )
                to_object_class_name = None
            if is_server_version_14:
                if not isinstance(to_object_class_name, str):
                    raise TypeError(
                        "'to_object_class_name' must be of type str or None. "
                        f"Given type: {type(to_object_class_name)}"
                    )
                to_object_class_name = _capitalize_first_letter(to_object_class_name)

        self._reference_batch.add(
            from_object_class_name=_capitalize_first_letter(from_object_class_name),
            from_object_uuid=from_object_uuid,
            from_property_name=from_property_name,
            to_object_uuid=to_object_uuid,
            to_object_class_name=to_object_class_name,
        )

        if self._batching_type:
            self._auto_create()

    def _create_data(
        self,
        data_type: str,
        batch_request: BatchRequest,
    ) -> Response:
        """
        Create data in batches, either Objects or References. This does NOT guarantee
        that each batch item (only Objects) is added/created. This can lead to a successful
        batch creation but unsuccessful per batch item creation. See the Examples below.

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
        requests.ReadTimeout
            If the request time-outed.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """
        try:
            timeout_count = connection_count = batch_error_count = 0
            while True:
                try:
                    response = self._connection.post(
                        path="/batch/" + data_type, weaviate_object=batch_request.get_request_body()
                    )
                except ReadTimeout as error:
                    batch_request = self._batch_readd_after_timeout(data_type, batch_request)
                    _batch_create_error_handler(
                        retry=timeout_count,
                        max_retries=self._timeout_retries,
                        error=error,
                    )
                    timeout_count += 1

                except RequestsConnectionError as error:
                    _batch_create_error_handler(
                        retry=connection_count,
                        max_retries=self._connection_error_retries,
                        error=error,
                    )
                    connection_count += 1
                else:
                    response_json = response.json()
                    if (
                        self._weaviate_error_retry is not None
                        and batch_error_count < self._weaviate_error_retry.number_retries
                    ):
                        batch_to_retry, response_json_successful = self._retry_on_error(
                            response_json, data_type
                        )
                        if len(batch_to_retry) > 0:
                            self._run_callback(response_json_successful)

                            batch_error_count += 1
                            batch_request = batch_to_retry
                            continue  # run the request again, but only with objects that had errors

                    self._run_callback(response_json)
                    break
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Batch was not added to weaviate.") from conn_err
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

    def _run_callback(self, response: BatchResponse):
        if self._callback is None:
            return
        # We don't know if user-supplied functions are threadsafe
        with self._callback_lock:
            self._callback(response)

    def _batch_readd_after_timeout(
        self, data_type: str, batch_request: BatchRequest
    ) -> BatchRequest:
        """
        Readds items (objects or references) that were not added due to a timeout.

        Parameters
        ----------
        data_type : str
            The Batch Request type, can be either 'objects' or 'references'.
        batch_request : BatchRequest
            The Batch Request that TimeOuted.

        Returns
        -------
        BatchRequest
            New Batch Request with objects that were not added or not updated.
        """

        if data_type == "objects":
            return self._readd_objects_after_timeout(batch_request)
        else:
            return self._readd_references_after_timeout(batch_request)

    def _readd_objects_after_timeout(
        self, batch_request: ObjectsBatchRequest
    ) -> ObjectsBatchRequest:
        """
        Read all objects that were not created or updated because of a TimeOut error.

        Parameters
        ----------
        batch_request : ObjectsBatchRequest
            The ObjectsBatchRequest from which to check if items where created or updated.

        Returns
        -------
        ObjectsBatchRequest
            New ObjectsBatchRequest with only the objects that were not created or updated.
        """

        new_batch = ObjectsBatchRequest()
        for obj in batch_request.get_request_body()["objects"]:
            class_name = obj["class"]
            uuid = obj["id"]
            response_head = self._connection.head(
                path="/objects/" + class_name + "/" + uuid,
            )

            if response_head.status_code == 404:
                new_batch.add(
                    class_name=_capitalize_first_letter(class_name),
                    data_object=obj["properties"],
                    uuid=uuid,
                    vector=obj.get("vector", None),
                )
                continue

            # object might already exist and needs to be overwritten in case of an update
            response = self._connection.get(
                path="/objects/" + class_name + "/" + uuid,
            )

            obj_weav = response.json()
            if obj_weav["properties"] != obj["properties"] or obj.get(
                "vector", None
            ) != obj_weav.get("vector", None):
                new_batch.add(
                    class_name=_capitalize_first_letter(class_name),
                    data_object=obj["properties"],
                    uuid=uuid,
                    vector=obj.get("vector", None),
                )
        return new_batch

    def _readd_references_after_timeout(
        self, batch_request: ReferenceBatchRequest
    ) -> ReferenceBatchRequest:
        """
        Read all objects that were not created or updated because of a TimeOut error.

        Parameters
        ----------
        batch_request : ReferenceBatchRequest
            The ReferenceBatchRequest from which to check if items where created or updated.

        Returns
        -------
        ReferenceBatchRequest
            New ReferenceBatchRequest with only the references that were not created or updated.
        """

        new_batch = ReferenceBatchRequest()
        for ref in batch_request.get_request_body():
            new_batch.add(
                from_object_class_name=ref["from_object_class_name"],
                from_object_uuid=ref["from_object_uuid"],
                from_property_name=ref["from_property_name"],
                to_object_uuid=ref["to_object_uuid"],
                to_object_class_name=ref.get("to_object_class_name", None),
            )
        return new_batch

    def create_objects(self) -> list:
        """
        Creates multiple Objects at once in Weaviate. This does not guarantee that each batch item
        is added/created to the Weaviate server. This can lead to a successful batch creation but
        unsuccessful per batch item creation. See the example bellow.
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
            _Warnings.manual_batching()

            response = self._create_data(
                data_type="objects",
                batch_request=self._objects_batch,
            )
            self._objects_batch = ObjectsBatchRequest()

            self._objects_throughput_frame.append(
                len(self._objects_batch) / response.elapsed.total_seconds()
            )
            obj_per_second = sum(self._objects_throughput_frame) / len(
                self._objects_throughput_frame
            )

            self._recommended_num_objects = round(obj_per_second * self._creation_time)

            return response.json()
        return []

    def create_references(self) -> list:
        """
        Creates multiple References at once in Weaviate.
        Adding References in batch is faster but it ignores validations like class name
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
        required criteria (See the documentation of the 'weaviate.Batch.add_reference' method
        for more information).

        >>> result = client.batch.create_references()

        As it can be noticed the reference batch creation is successful (no error thrown). Now we
        can inspect the 'result'.

        >>> import json
        >>> print(json.dumps(result, indent=4))
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
            _Warnings.manual_batching()

            response = self._create_data(
                data_type="references",
                batch_request=self._reference_batch,
            )
            self._reference_batch = ReferenceBatchRequest()

            self._references_throughput_frame.append(
                len(self._reference_batch) / response.elapsed.total_seconds()
            )
            ref_per_sec = sum(self._references_throughput_frame) / len(
                self._references_throughput_frame
            )

            self._recommended_num_references = round(ref_per_sec * self._creation_time)

            return response.json()
        return []

    def _flush_in_thread(
        self,
        data_type: str,
        batch_request: BatchRequest,
    ) -> Tuple[Optional[Response], int]:
        """
        Flush BatchRequest in current thread/process.

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
        Tuple[requests.Response, int]
            The request response and number of items sent with the BatchRequest as tuple.
        """

        if len(batch_request) != 0:
            response = self._create_data(
                data_type=data_type,
                batch_request=batch_request,
            )
            return response, len(batch_request)
        return None, 0

    def _send_batch_requests(self, force_wait: bool) -> None:
        """
        Send BatchRequest in a separate thread/process. This methods submits a task to create only
        the ObjectsBatchRequests to the BatchExecutor and adds the ReferencesBatchRequests to a
        queue, then it carries on in the main thread until `num_workers` tasks have been submitted.
        When we have reached number of tasks to be equal to `num_workers` it waits for all the
        tasks to finish and handles the responses. After all ObjectsBatchRequests have been handled
        it created separate tasks for each ReferencesBatchRequests, then it handles their responses
        as well. This mechanism of creating References after Objects is constructed in this manner
        to eliminate potential error when creating references from a object that does not yet
        exists (object that is part of another task).

        Parameters
        ----------
        force_wait : bool
            Whether to wait on all created tasks even if we do not have `num_workers` tasks created
        """
        if self._executor is None:
            self.start()
        elif self._executor.is_shutdown():
            warnings.warn(
                message=BATCH_EXECUTOR_SHUTDOWN_W,
                category=RuntimeWarning,
                stacklevel=1,
            )
            self.start()

        future = self._executor.submit(
            self._flush_in_thread,
            data_type="objects",
            batch_request=self._objects_batch,
        )

        self._future_pool.append(future)
        if len(self._reference_batch) > 0:
            self._reference_batch_queue.append(self._reference_batch)

        self._objects_batch = ObjectsBatchRequest()
        self._reference_batch = ReferenceBatchRequest()

        if not force_wait and self._num_workers > 1 and len(self._future_pool) < self._num_workers:
            return
        timeout_occurred = False
        for done_future in as_completed(self._future_pool):

            response_objects, nr_objects = done_future.result()

            # handle objects response
            if response_objects is not None:
                self._objects_throughput_frame.append(
                    nr_objects / response_objects.elapsed.total_seconds()
                )

            else:
                timeout_occurred = True

        if timeout_occurred and self._recommended_num_objects is not None:
            self._recommended_num_objects = max(self._recommended_num_objects // 2, 1)
        elif len(self._objects_throughput_frame) != 0 and self._recommended_num_objects is not None:
            obj_per_second = (
                sum(self._objects_throughput_frame) / len(self._objects_throughput_frame) * 0.75
            )
            self._recommended_num_objects = min(
                round(obj_per_second * self._creation_time),
                self._recommended_num_objects + 250,
            )
        # Create references after all the objects have been created
        reference_future_pool = []
        for reference_batch in self._reference_batch_queue:
            future = self._executor.submit(
                self._flush_in_thread,
                data_type="references",
                batch_request=reference_batch,
            )
            reference_future_pool.append(future)

        timeout_occurred = False
        for done_future in as_completed(reference_future_pool):

            response_references, nr_references = done_future.result()

            # handle references response
            if response_references is not None:
                self._references_throughput_frame.append(
                    nr_references / response_references.elapsed.total_seconds()
                )
            else:
                timeout_occurred = True

        if timeout_occurred and self._recommended_num_objects is not None:
            self._recommended_num_references = max(self._recommended_num_references // 2, 1)
        elif (
            len(self._references_throughput_frame) != 0
            and self._recommended_num_references is not None
        ):
            ref_per_sec = sum(self._references_throughput_frame) / len(
                self._references_throughput_frame
            )
            self._recommended_num_references = min(
                round(ref_per_sec * self._creation_time),
                self._recommended_num_references * 2,
            )

        self._future_pool = []
        self._reference_batch_queue = []
        return

    def _auto_create(self) -> None:
        """
        Auto create both objects and references in the batch. This protected method works with a
        fixed batch size and with dynamic batching. For a 'fixed' batching type it auto-creates
        when the sum of both objects and references equals batch_size. For dynamic batching it
        creates both batch requests when only one is full.
        """

        # greater or equal in case the self._batch_size is changed manually
        if self._batching_type == "fixed":
            if sum(self.shape) >= self._batch_size:
                self._send_batch_requests(force_wait=False)
            return
        elif self._batching_type == "dynamic":
            if (
                self.num_objects() >= self._recommended_num_objects
                or self.num_references() >= self._recommended_num_references
            ):
                self._send_batch_requests(force_wait=False)
            return
        # just in case
        raise ValueError(f'Unsupported batching type "{self._batching_type}"')

    def flush(self) -> None:
        """
        Flush both objects and references to the Weaviate server and call the callback function
        if one is provided. (See the docs for `configure` or `__call__` for how to set one.)
        """
        self._send_batch_requests(force_wait=True)

    def delete_objects(
        self,
        class_name: str,
        where: dict,
        output: str = "minimal",
        dry_run: bool = False,
    ) -> dict:
        """
        Delete objects that match the 'match' in batch.

        Parameters
        ----------
        class_name : str
            The class name for which to delete objects.
        where : dict
            The content of the `where` filter used to match objects that should be deleted.
        output : str, optional
            The control of the verbosity of the output, possible values:
            - "minimal" : The result only includes counts. Information about objects is omitted if
            the deletes were successful. Only if an error occurred will the object be described.
            - "verbose" : The result lists all affected objects with their ID and deletion status,
            including both successful and unsuccessful deletes.
            By default "minimal"
        dry_run : bool, optional
            If True, objects will not be deleted yet, but merely listed, by default False

        Examples
        --------

        If we want to delete all the data objects that contain the word 'weather' we can do it like
        this:

        >>> result = client.batch.delete_objects(
        ...     class_name='Dataset',
        ...     output='verbose',
        ...     dry_run=False,
        ...     where={
        ...         'operator': 'Equal',
        ...         'path': ['description'],
        ...         'valueText': 'weather'
        ...     }
        ... )
        >>> print(json.dumps(result, indent=4))
        {
            "dryRun": false,
            "match": {
                "class": "Dataset",
                "where": {
                    "operands": null,
                    "operator": "Equal",
                    "path": [
                        "description"
                    ],
                    "valueText": "weather"
                }
            },
            "output": "verbose",
            "results": {
                "failed": 0,
                "limit": 10000,
                "matches": 2,
                "objects": [
                    {
                        "id": "1eb28f69-c66e-5411-bad4-4e14412b65cd",
                        "status": "SUCCESS"
                    },
                    {
                        "id": "da217bdd-4c7c-5568-9576-ebefe17688ba",
                        "status": "SUCCESS"
                    }
                ],
                "successful": 2
            }
        }

        Returns
        -------
        dict
            The result/status of the batch delete.
        """

        if not isinstance(class_name, str):
            raise TypeError(f"'class_name' must be of type str. Given type: {type(class_name)}.")
        if not isinstance(where, dict):
            raise TypeError(f"'where' must be of type dict. Given type: {type(class_name)}.")
        if not isinstance(output, str):
            raise TypeError(f"'output' must be of type str. Given type: {type(class_name)}.")
        if not isinstance(dry_run, bool):
            raise TypeError(f"'dry_run' must be of type bool. Given type: {type(class_name)}.")

        payload = {
            "match": {
                "class": class_name,
                "where": where,
            },
            "output": output,
            "dryRun": dry_run,
        }

        try:
            response = self._connection.delete(
                path="/batch/objects",
                weaviate_object=payload,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Batch delete was not successful.") from conn_err
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException("Delete in batch", response)

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

    def pop_object(self, index: int = -1) -> dict:
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

    def pop_reference(self, index: int = -1) -> dict:
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

        _check_positive_num(value, "batch_size", int)
        self._batch_size = value
        if self._batching_type is None:
            self._batching_type = "fixed"
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

        return self._batching_type == "dynamic"

    @dynamic.setter
    def dynamic(self, value: bool) -> None:

        if self._batching_type is None:
            return

        _check_bool(value, "dynamic")

        if value is True:
            self._batching_type = "dynamic"
        else:
            self._batching_type = "fixed"
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

    def start(self) -> "Batch":
        """
        Start the BatchExecutor if it was closed.

        Returns
        -------
        Batch
            Updated self.
        """

        if self._executor is None or self._executor.is_shutdown():
            self._executor = BatchExecutor(max_workers=self._num_workers)
        return self

    def shutdown(self) -> None:
        """
        Shutdown the BatchExecutor.
        """
        if not (self._executor is None or self._executor.is_shutdown()):
            self._executor.shutdown()

    def __enter__(self) -> "Batch":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.shutdown()

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

        _check_positive_num(value, "creation_time", Real)
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

        Properties
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

        _check_non_negative(value, "timeout_retries", int)
        self._timeout_retries = value

    @property
    def connection_error_retries(self) -> int:
        """
        Setter and Getter for `connection_error_retries`.

        Properties
        ----------
        value : int
            Setter ONLY: The new value for `connection_error_retries`.

        Returns
        -------
        int
            Getter ONLY: The `connection_error_retries` value.

        Raises
        ------
        TypeError
            Setter ONLY: If the new value is not of type int.
        ValueError
            Setter ONLY: If the new value has a non positive value.
        """

        return self._connection_error_retries

    @connection_error_retries.setter
    def connection_error_retries(self, value: int) -> None:
        _check_non_negative(value, "connection_error_retries", int)
        self._connection_error_retries = value

    def _retry_on_error(
        self, response: BatchResponse, data_type: str
    ) -> Tuple[BatchRequestType, BatchResponse]:
        if data_type == "objects":
            new_batch = ObjectsBatchRequest()
        else:
            new_batch = ReferenceBatchRequest()
        successful_responses = new_batch.add_failed_objects_from_response(
            response,
            self._weaviate_error_retry.errors_to_exclude,
            self._weaviate_error_retry.errors_to_include,
        )
        return new_batch, successful_responses


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


def _batch_create_error_handler(retry: int, max_retries: int, error: Exception) -> None:
    """
    Handle errors that occur in Batch creation. This function is going to re-raise the error if
    number of re-tries was reached.
    Parameters
    ----------
    retry : int
        Current number of attempted request calls.
    max_retries : int
        Maximum number of attempted request calls.
    error : Exception
        The exception that occurred (to be re-raised if needed).
    Raises
    ------
    Exception
        The caught exception.
    """

    if retry >= max_retries:
        raise error
    print(
        f"[ERROR] Batch {error.__class__.__name__} Exception occurred! Retrying in "
        f"{(retry + 1) * 2}s. [{retry + 1}/{max_retries}]",
        file=sys.stderr,
        flush=True,
    )
    time.sleep((retry + 1) * 2)
