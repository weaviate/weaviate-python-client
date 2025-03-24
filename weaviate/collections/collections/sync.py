from typing import Optional, Type
from weaviate.collections.collections.async_ import _CollectionsAsync, _CollectionsBase
from weaviate.collections.classes.internal import Properties, References
from weaviate.collections.collection.sync import Collection
from weaviate.connect.v4 import ConnectionSync
from weaviate import syncify


@syncify.convert_new(_CollectionsAsync)
class _Collections(_CollectionsBase[ConnectionSync]):
    def get(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Collection[Properties, References]:
        """Use this method to return a collection object to be used when interacting with your Weaviate collection.

        This method does not send a request to Weaviate. It simply creates a Python object for you to use to make requests.

        Arguments:
            `name`
                The name of the collection to get.
            `data_model_properties`
                The generic class that you want to use to represent the properties of objects in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return objects properties as `Dict[str, Any]`.
            `data_model_references`
                The generic class that you want to use to represent the objects of references in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return properties of referenced objects as `Dict[str, Any]`.
            `skip_argument_validation`
                If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.
        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.exceptions.InvalidDataModelException`
                If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        return self.use(
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )

    def use(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Collection[Properties, References]:
        """Use this method to return a collection object to be used when interacting with your Weaviate collection.

        This method does not send a request to Weaviate. It simply creates a Python object for you to use to make requests.

        Arguments:
            `name`
                The name of the collection to get.
            `data_model_properties`
                The generic class that you want to use to represent the properties of objects in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return objects properties as `Dict[str, Any]`.
            `data_model_references`
                The generic class that you want to use to represent the objects of references in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return properties of referenced objects as `Dict[str, Any]`.
            `skip_argument_validation`
                If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.
        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.exceptions.InvalidDataModelException`
                If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        collection = self._executor.use(
            connection=self._connection,
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )
        assert isinstance(collection, Collection)
        return collection
