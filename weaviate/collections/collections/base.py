from abc import abstractmethod
from typing import (
    Awaitable,
    Generic,
    Optional,
    Type,
    Union,
)

from weaviate.collections.classes.config import (
    CollectionConfig,
)
from weaviate.collections.classes.internal import References
from weaviate.collections.classes.types import (
    Properties,
)
from weaviate.collections.collection import CollectionAsync, Collection
from weaviate.collections.collections.executor import _CollectionsExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType


class _CollectionsBase(Generic[ConnectionType], _CollectionsExecutor[ConnectionType]):
    def __init__(self, connection: ConnectionType) -> None:
        self._connection = connection

    @executor.no_wrapping
    def get(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Union[Collection[Properties, References], CollectionAsync[Properties, References]]:
        """Use this method to return a collection object to be used when interacting with your Weaviate collection.

        This method does not send a request to Weaviate. It simply creates a Python object for you to use to make requests.

        Args:
            name: The name of the collection to get.
            data_model_properties: The generic class that you want to use to represent the properties of objects in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return objects properties as `Dict[str, Any]`.
            data_model_references: The generic class that you want to use to represent the objects of references in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return properties of referenced objects as `Dict[str, Any]`.
            skip_argument_validation: If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.InvalidDataModelException: If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        return self.use(
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )

    @abstractmethod
    def use(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Union[Collection[Properties, References], CollectionAsync[Properties, References]]:
        """Use this method to return a collection object to be used when interacting with your Weaviate collection.

        This method does not send a request to Weaviate. It simply creates a Python object for you to use to make requests.

        Args:
            name: The name of the collection to get.
            data_model_properties: The generic class that you want to use to represent the properties of objects in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return objects properties as `Dict[str, Any]`.
            data_model_references: The generic class that you want to use to represent the objects of references in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return properties of referenced objects as `Dict[str, Any]`.
            skip_argument_validation: If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.InvalidDataModelException: If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        raise NotImplementedError()

    @abstractmethod
    def create_from_dict(
        self, config: dict
    ) -> Union[
        Collection[Properties, References], Awaitable[CollectionAsync[Properties, References]]
    ]:
        """Use this method to create a collection in Weaviate and immediately return a collection object using a pre-defined Weaviate collection configuration dictionary object.

        This method is helpful for those making the v3 -> v4 migration and for those interfacing with any experimental
        Weaviate features that are not yet fully supported by the Weaviate Python client.

        Args:
            config: The dictionary representation of the collection's configuration.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def create_from_config(
        self, config: CollectionConfig
    ) -> Union[
        Collection[Properties, References], Awaitable[CollectionAsync[Properties, References]]
    ]:
        """Use this method to create a collection in Weaviate and immediately return a collection object using a pre-defined Weaviate collection configuration object.

        Args:
            config: The collection's configuration.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()
