"""
BatchRequest class definitions.
"""

import copy
from abc import ABC, abstractmethod
from typing import List, Sequence, Optional, Dict, Any, Union
from uuid import uuid4

from weaviate.util import get_valid_uuid, get_vector
from weaviate.types import UUID

BatchResponse = List[Dict[str, Any]]


class BatchRequest(ABC):
    """
    BatchRequest abstract class used as a interface for batch requests.
    """

    def __init__(self) -> None:
        self._items: List[Dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        """
        Check if BatchRequest is empty.

        Returns
        -------
        bool
            Whether the BatchRequest is empty.
        """

        return len(self._items) == 0

    def empty(self) -> None:
        """
        Remove all the items from the BatchRequest.
        """

        self._items = []

    def pop(self, index: int = -1) -> dict:
        """
        Remove and return item at index (default last).

        Parameters
        ----------
        index : int, optional
            The index of the item to pop, by default -1 (last item).

        Returns
        -------
        dict
            The popped item.

        Raises
        -------
        IndexError
            If batch is empty or index is out of range.
        """

        return self._items.pop(index)

    @abstractmethod
    def add(self, *args, **kwargs):  # type: ignore
        """Add objects to BatchRequest."""

    @abstractmethod
    def get_request_body(self) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
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


class ReferenceBatchRequest(BatchRequest):
    """
    Collect Weaviate-object references to add them in one request to Weaviate.
    Caution this request will miss some validations to be faster.
    """

    def add(  # pyright: ignore reportIncompatibleMethodOverride
        self,
        from_object_class_name: str,
        from_object_uuid: UUID,
        from_property_name: str,
        to_object_uuid: UUID,
        to_object_class_name: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """
        Add one Weaviate-object reference to this batch. Does NOT validate the consistency of the
        reference against the class schema. Checks the arguments' type and UUIDs' format.

        Parameters
        ----------
        from_object_class_name : str
            The name of the class that should reference another object.
        from_object_uuid : str
            The UUID or URL of the object that should reference another object.
        from_property_name : str
            The name of the property that contains the reference.
        to_object_uuid : str
            The UUID or URL of the object that is actually referenced.
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

        if not isinstance(from_object_class_name, str):
            raise TypeError("'from_object_class_name' argument must be of type str")

        if not isinstance(from_property_name, str):
            raise TypeError("'from_property_name' argument must be of type str")

        if to_object_class_name is not None and not isinstance(to_object_class_name, str):
            raise TypeError("'to_object_class_name' argument must be of type str")

        to_object_uuid = get_valid_uuid(to_object_uuid)
        from_object_uuid = get_valid_uuid(from_object_uuid)

        if to_object_class_name is not None:
            to_beacon = f"weaviate://localhost/{to_object_class_name}/{to_object_uuid}"
        else:
            to_beacon = f"weaviate://localhost/{to_object_uuid}"

        item = {
            "from": "weaviate://localhost/"
            + from_object_class_name
            + "/"
            + from_object_uuid
            + "/"
            + from_property_name,
            "to": to_beacon,
        }

        if tenant is not None:
            item["tenant"] = tenant

        self._items.append(item)

    def get_request_body(self) -> List[Dict[str, Any]]:
        """
        Get request body as a list of dictionaries, where each dictionary
        is a Weaviate-object reference.

        Returns
        -------
        List[dict]
            A list of Weaviate-objects references as dictionaries.
        """

        return self._items

    def add_failed_objects_from_response(  # pyright: ignore reportIncompatibleMethodOverride
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
            self._items.append({"from": ref["from"], "to": ref["to"]})
        return successful_responses


class ObjectsBatchRequest(BatchRequest):
    """
    Collect objects for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def add(  # pyright: ignore reportIncompatibleMethodOverride
        self,
        data_object: dict,
        class_name: str,
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
        tenant: Optional[str] = None,
    ) -> str:
        """
        Add one object to this batch. Does NOT validate the consistency of the object against
        the client's schema. Checks the arguments' type and UUIDs' format.

        Parameters
        ----------
        class_name : str
            The name of the class this object belongs to.
        data_object : dict
            Object to be added as a dict datatype.
        uuid : str or None, optional
            UUID of the object as a string, by default None
        vector: Sequence or None, optional
            The embedding of the object that should be validated.
            Can be used when:
             - a class does not have a vectorization module.
             - The given vector was generated using the _identical_ vectorization module that is configured for the
             class. In this case this vector takes precedence.

            Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`,
            by default None.
        tenant: str, optional
            Tenant of the object

        Returns
        -------
        str
            The UUID of the added object. If one was not provided a UUIDv3 will be generated.

        Raises
        ------
        TypeError
            If an argument passed is not of an appropriate type.
        ValueError
            If 'uuid' is not of a proper form.
        """

        if not isinstance(data_object, dict):
            raise TypeError("Object must be of type dict")
        if not isinstance(class_name, str):
            raise TypeError("Class name must be of type str")

        batch_item = {"class": class_name, "properties": copy.deepcopy(data_object)}
        if uuid is not None:
            valid_uuid = get_valid_uuid(uuid)
        else:
            valid_uuid = get_valid_uuid(uuid4())
        batch_item["id"] = valid_uuid

        if vector is not None:
            batch_item["vector"] = get_vector(vector)
        if tenant is not None:
            batch_item["tenant"] = tenant

        self._items.append(batch_item)

        return valid_uuid

    def get_request_body(self) -> Dict[str, Any]:
        """
        Get the request body as it is needed for the Weaviate server.

        Returns
        -------
        dict
            The request body as a dict.
        """

        return {"fields": ["ALL"], "objects": self._items}

    def add_failed_objects_from_response(  # pyright: ignore reportIncompatibleMethodOverride
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
                data_object=obj["properties"],
                class_name=obj["class"],
                uuid=obj["id"],
                vector=obj.get("vector", None),
                tenant=obj.get("tenant", None),
            )
        return successful_responses
