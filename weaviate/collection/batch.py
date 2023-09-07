import time
from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from threading import Event, Thread
from typing import Any, Deque, Dict, Generic, List, Optional, Tuple, TypeVar, Union


from requests import ReadTimeout, Response
from requests.exceptions import HTTPError as RequestsHTTPError

from weaviate.cluster import Cluster
from weaviate.collection.classes.batch import (
    BatchObject,
    BatchReference,
    BatchObjectRequestBody,
    _BatchObject,
    _BatchReference,
    _BatchReturn,
)
from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.grpc_batch import _BatchGRPC
from weaviate.connect import Connection
from weaviate.warnings import _Warnings
from weaviate.weaviate_types import UUID


class BatchExecutor(ThreadPoolExecutor):
    """
    Weaviate Batch Executor to run batch requests in separate thread.
    This class implements an additional method `is_shutdown` that is used by the context manager.
    """

    def is_shutdown(self) -> bool:
        return self._shutdown


class _Batch:
    def __init__(self, connection: Connection):
        self.__batch_objects = ObjectsBatchRequest()
        self.__batch_references = ReferenceBatchRequest()
        self.__batch_size: Optional[int] = 50
        self.__connection = connection
        self.__consistency_level: Optional[ConsistencyLevel] = None
        self.__creation_time = min(self.__connection.timeout_config[1] / 10, 2)
        self.__batch = _BatchGRPC(connection, self.__consistency_level)
        self.__executor: Optional[BatchExecutor] = None
        self.__future_pool_objects: List[Future[Tuple[Optional[_BatchReturn], int]]] = []
        self.__future_pool_references: List[Future[Tuple[Optional[Response], int]]] = []
        self.__new_dynamic_batching = True
        self.__num_workers: int = 1
        self.__objects_throughput_frame: Deque[float] = deque(maxlen=5)
        self.__recommended_num_objects = self.__batch_size
        self.__recommended_num_references = self.__batch_size
        self.__reference_batch_queue: List[ReferenceBatchRequest] = []
        self.__references_throughput_frame: Deque[float] = deque(maxlen=5)
        self.__shutdown_background_event: Optional[Event] = None

    def num_objects(self) -> int:
        """
        Get current number of objects in the batch.

        Returns
            `int` The number of objects in the batch.
        """

        return len(self.__batch_objects)

    def num_references(self) -> int:
        """
        Get current number of references in the batch.

        Returns
            `int` The number of references in the batch.
        """

        return len(self.__batch_references)

    def start(self) -> "_Batch":
        """
        Start the BatchExecutor if it was closed.

        Returns
            `Batch`
                Updated self.
        """

        if self.__executor is None or self.__executor.is_shutdown():
            self.__executor = BatchExecutor(max_workers=self.__num_workers)

        if self.__shutdown_background_event is None or self.__shutdown_background_event.is_set():
            self.__update_recommended_batch_size()

        return self

    def shutdown(self) -> None:
        """
        Shutdown the BatchExecutor.
        """
        if not (self.__executor is None or self.__executor.is_shutdown()):
            self.__executor.shutdown()

        if self.__shutdown_background_event is not None:
            self.__shutdown_background_event.set()

    def flush(self) -> None:
        """
        Flush both objects and references to the Weaviate server and call the callback function
        if one is provided. (See the docs for `configure` or `__call__` for how to set one.)
        """
        self.__send_batch_requests(force_wait=True)

    def __enter__(self) -> "_Batch":
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.flush()
        self.shutdown()

    def add_object(self, object_: BatchObject) -> UUID:
        """
        Add one object to this batch.
        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Parameters
            `object_` Pydantic `BatchObject` model that supports complete validation of the Weaviate object
                at the point of creation and insertion. If your data is invalid, you will receive `ValidationError`s
                from Pydantic when creating your `BatchObject` model.

        Returns
            `str` The UUID of the added object. If one was not provided a UUIDv4 will be generated.
        """
        uuid = self.__batch_objects.add(object_._to_internal())
        self.__auto_create()
        return uuid

    def add_reference(self, reference: BatchReference) -> None:
        """
        Add one reference to this batch.

        Parameters
            `reference` Pydantic `BatchReference` model that supports complete validation of the Weaviate reference
                at the point of creation and insertion. If your data is invalid, you will receive `ValidationError`s
                from Pydantic when creating your `BatchReference` model.
        """
        self.__batch_references.add(reference._to_internal())
        self.__auto_create()

    def __auto_create(self) -> None:
        if (
            self.num_objects() >= self.__recommended_num_objects
            or self.num_references() >= self.__recommended_num_objects
        ):
            while self.__recommended_num_objects == 0:
                time.sleep(1)  # block if weaviate is overloaded

            self.__send_batch_requests(force_wait=False)
        return

    def __flush_objects(self, batch: List[_BatchObject]) -> Tuple[Optional[_BatchReturn], int]:
        if len(batch) != 0:
            return_ = self.__batch.objects(
                objects=batch,
            )
            return return_, len(batch)
        return None, 0

    def __flush_references(self, batch: List[_BatchReference]) -> Tuple[Optional[Response], int]:
        if len(batch) != 0:
            response = self.__batch.references(
                references=batch,
            )
            return response, len(batch)
        return None, 0

    def __send_batch_requests(self, force_wait: bool) -> None:
        if self.__executor is None:
            self.start()
        elif self.__executor.is_shutdown():
            _Warnings.batch_executor_is_shutdown()
            self.start()

        assert self.__executor is not None
        obj_future = self.__executor.submit(
            self.__flush_objects,
            batch=self.__batch_objects._items,
        )

        self.__future_pool_objects.append(obj_future)
        if len(self.__batch_references) > 0:
            self.__reference_batch_queue.append(self.__batch_references)

        self.__batch_objects.clear()
        self.__batch_references.clear()

        if (
            not force_wait
            and self.__num_workers > 1
            and len(self.__future_pool_objects) < self.__num_workers
        ):
            return
        timeout_occurred = False
        for done_obj_future in as_completed(self.__future_pool_objects):
            response_objects, nr_objects = done_obj_future.result()

            # handle objects response
            if response_objects is not None:
                self.__objects_throughput_frame.append(
                    nr_objects / response_objects.elapsed_seconds
                )

            else:
                timeout_occurred = True

        if timeout_occurred and self.__recommended_num_objects is not None:
            self.__recommended_num_objects = max(self.__recommended_num_objects // 2, 1)
        elif (
            len(self.__objects_throughput_frame) != 0
            and self.__recommended_num_objects is not None
            and not self.__new_dynamic_batching
        ):
            obj_per_second = (
                sum(self.__objects_throughput_frame) / len(self.__objects_throughput_frame) * 0.75
            )
            self.__recommended_num_objects = max(
                min(
                    round(obj_per_second * self.__creation_time),
                    self.__recommended_num_objects + 250,
                ),
                1,
            )

        for reference_batch in self.__reference_batch_queue:
            ref_future = self.__executor.submit(
                self.__flush_references,
                batch=reference_batch._items,
            )
            self.__future_pool_references.append(ref_future)

        timeout_occurred = False
        for done_ref_future in as_completed(self.__future_pool_references):
            response_references, nr_references = done_ref_future.result()

            # handle references response
            if response_references is not None:
                self.__references_throughput_frame.append(
                    nr_references / response_references.elapsed.total_seconds()
                )
            else:
                timeout_occurred = True

        if timeout_occurred and self.__recommended_num_references is not None:
            self.__recommended_num_references = max(self.__recommended_num_references // 2, 1)
        elif (
            len(self.__references_throughput_frame) != 0
            and self.__recommended_num_references is not None
        ):
            ref_per_sec = sum(self.__references_throughput_frame) / len(
                self.__references_throughput_frame
            )
            self.__recommended_num_references = min(
                round(ref_per_sec * self.__creation_time),
                self.__recommended_num_references * 2,
            )

        self.__future_pool_objects = []
        self.__future_pool_references = []
        self.__reference_batch_queue = []
        return

    def __update_recommended_batch_size(self) -> None:
        """Create a background process that periodically checks how congested the batch queue is."""
        self.__shutdown_background_event = Event()

        def periodic_check() -> None:
            cluster = Cluster(self.__connection)
            while (
                self.__shutdown_background_event is not None
                and not self.__shutdown_background_event.is_set()
            ):
                try:
                    status = cluster.get_nodes_status()
                    if "stats" not in status[0] or "ratePerSecond" not in status[0]["stats"]:
                        self.__new_dynamic_batching = False
                        return
                    rate = status[0]["batchStats"]["ratePerSecond"]
                    rate_per_worker = rate / self.__num_workers
                    batch_length = status[0]["batchStats"]["queueLength"]

                    if batch_length == 0:  # scale up if queue is empty
                        self.__recommended_num_objects = self.__recommended_num_objects + min(
                            self.__recommended_num_objects * 2, 25
                        )
                    else:
                        ratio = batch_length / rate
                        if (
                            2.1 > ratio > 1.9
                        ):  # ideal, send exactly as many objects as weaviate can process
                            self.__recommended_num_objects = rate_per_worker
                        elif ratio <= 1.9:  # we can send more
                            self.__recommended_num_objects = min(
                                self.__recommended_num_objects * 1.5, rate_per_worker * 2 / ratio
                            )
                        elif ratio < 10:  # too high, scale down
                            self.__recommended_num_objects = rate_per_worker * 2 / ratio
                        else:  # way too high, stop sending new batches
                            self.__recommended_num_objects = 0

                    refresh_time: float = 2
                except (RequestsHTTPError, ReadTimeout):
                    refresh_time = 0.1

                time.sleep(refresh_time)
            self.__recommended_num_objects = 10  # in case some batch needs to be send afterwards
            self.__shutdown_background_event = None

        demon = Thread(
            target=periodic_check,
            daemon=True,
            name="batchSizeRefresh",
        )
        demon.start()


BatchResponse = List[Dict[str, Any]]


TBatchObject = TypeVar("TBatchObject")


class BatchRequest(ABC, Generic[TBatchObject]):
    """
    `BatchRequest` abstract class used as a interface for batch requests.
    """

    def __init__(self) -> None:
        self._items: List[TBatchObject] = []

    def __len__(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        """
        Check if `BatchRequest` is empty.

        Returns
            `bool` Whether the `BatchRequest` is empty.
        """

        return len(self._items) == 0

    def clear(self) -> None:
        """
        Remove all the items from the BatchRequest.
        """

        self._items = []

    def pop(self, index: int = -1) -> TBatchObject:
        """
        Remove and return item at index (default last).

        Parameters
            `index` index of the item to pop, by default -1 (last item).

        Returns
            `TBatchObject` The popped item.

        Raises
            `IndexError` If batch is empty or index is out of range.
        """

        return self._items.pop(index)

    @abstractmethod
    def add(self, *args, **kwargs):  # type: ignore
        """Add objects to BatchRequest."""

    @abstractmethod
    def get_request_body(self) -> Union[List[TBatchObject], BatchObjectRequestBody]:
        """Return the request body to be digested by weaviate that contains all batch items."""

    @abstractmethod
    def add_failed_objects_from_response(
        self,
        response_item: BatchResponse,
        errors_to_exclude: Optional[List[str]],
        errors_to_include: Optional[List[str]],
    ) -> BatchResponse:
        """Add failed items from a weaviate response.

        Parameters
        ----------
        response_item : BatchResponse
            Weaviate response that contains the status for all objects.
        errors_to_exclude : Optional[List[str]]
            Which errors should NOT be retried.
        errors_to_include : Optional[List[str]]
            Which errors should be retried.

        Returns
        ------
        BatchResponse: Contains responses form all successful object, eg. those that have not been added to this batch.
        """

    @staticmethod
    def _skip_objects_retry(
        entry: Dict[str, Any],
        errors_to_exclude: Optional[List[str]],
        errors_to_include: Optional[List[str]],
    ) -> bool:
        if (
            len(entry["result"]) == 0
            or "errors" not in entry["result"]
            or "error" not in entry["result"]["errors"]
            or len(entry["result"]["errors"]["error"]) == 0
        ):
            return True

        # skip based on error messages
        if errors_to_exclude is not None:
            for err in entry["result"]["errors"]["error"]:
                if any(excl in err["message"] for excl in errors_to_exclude):
                    return True
            return False
        elif errors_to_include is not None:
            for err in entry["result"]["errors"]["error"]:
                if any(incl in err["message"] for incl in errors_to_include):
                    return False
            return True
        return False


class ReferenceBatchRequest(BatchRequest[_BatchReference]):
    """
    Collect Weaviate-object references to add them in one request to Weaviate.
    Caution this request will miss some validations to be faster.
    """

    def add(self, reference: _BatchReference) -> None:
        """
        Add one Weaviate-object reference to this batch. Does NOT validate the consistency of the
        reference against the class schema. Checks the arguments' type and UUIDs' format.

        Parameters
            reference: `BatchReference`; A dataclass model for passing data to batching methods with type safety.
        """
        self._items.append(reference)

    def get_request_body(self) -> List[_BatchReference]:
        """
        Get request body as a list of dictionaries, where each dictionary
        is a Weaviate-object reference.

        Returns
            `List[BatchReference]` A list of Weaviate-objects references as dictionaries.
        """

        return self._items

    def add_failed_objects_from_response(
        self,
        response: BatchResponse,
        errors_to_exclude: Optional[List[str]],
        errors_to_include: Optional[List[str]],
    ) -> BatchResponse:
        successful_responses = []

        for ref in response:
            if self._skip_objects_retry(ref, errors_to_exclude, errors_to_include):
                successful_responses.append(ref)
                continue
            # self._items.append({"from": ref["from"], "to": ref["to"]})
        return successful_responses


class ObjectsBatchRequest(BatchRequest[_BatchObject]):
    """
    Collect objects for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def add(self, object_: _BatchObject) -> UUID:
        """
        Add one object to this batch. Does NOT validate the consistency of the object against
        the client's schema.

        Parameters
            object: `_BatchObject`; An internal dataclass model for passing data to batching methods with type safety.

        Returns
            `UUID` The UUID of the added object.
        """
        self._items.append(object_)
        assert object_.uuid is not None
        return object_.uuid

    def get_request_body(self) -> BatchObjectRequestBody:
        """
        Get the request body as it is needed for the Weaviate server.

        Returns
            `BatchObjectRequestBody` The request body as a dataclass.
        """

        return BatchObjectRequestBody(fields=["ALL"], objects=self._items)

    def add_failed_objects_from_response(
        self,
        response: BatchResponse,
        errors_to_exclude: Optional[List[str]],
        errors_to_include: Optional[List[str]],
    ) -> BatchResponse:
        successful_responses = []

        for obj in response:
            if self._skip_objects_retry(obj, errors_to_exclude, errors_to_include):
                successful_responses.append(obj)
                continue
            self.add(
                _BatchObject(
                    properties=obj["properties"],
                    class_name=obj["class"],
                    uuid=obj["id"],
                    vector=obj.get("vector", None),
                    tenant=obj.get("tenant", None),
                )
            )
        return successful_responses
