import asyncio
from typing import (
    Awaitable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from httpx import Response
from pydantic import ValidationError

from weaviate.collections.classes.config import (
    _NamedVectorConfigCreate,
    CollectionConfig,
    CollectionConfigSimple,
    _CollectionConfigCreate,
    _GenerativeProvider,
    _InvertedIndexConfigCreate,
    _MultiTenancyConfigCreate,
    _VectorIndexConfigCreate,
    Property,
    _ShardingConfigCreate,
    _ReferencePropertyBase,
    _ReplicationConfigCreate,
    _RerankerProvider,
    _VectorizerConfigCreate,
)
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_configs_from_json,
    _collection_configs_simple_from_json,
)
from weaviate.collections.classes.internal import References
from weaviate.collections.classes.types import (
    Properties,
    _check_properties_generic,
    _check_references_generic,
)
from weaviate.collections.collection import CollectionAsync, Collection
from weaviate.connect import executor
from weaviate.connect.v4 import (
    ConnectionType,
    ConnectionAsync,
    _ExpectedStatusCodes,
)
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict
from weaviate.validator import _validate_input, _ValidateArgument

CollectionType = TypeVar("CollectionType", Collection, CollectionAsync)


class _CollectionsExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def _use(
        self,
        *,
        name: str,
        data_model_properties: Optional[Type[Properties]],
        data_model_references: Optional[Type[References]],
        skip_argument_validation: bool = False,
    ) -> Union[CollectionAsync[Properties, References], Collection[Properties, References]]:
        if not skip_argument_validation:
            _validate_input([_ValidateArgument(expected=[str], name="name", value=name)])
            _check_properties_generic(data_model_properties)
            _check_references_generic(data_model_references)
        name = _capitalize_first_letter(name)
        if isinstance(self._connection, ConnectionAsync):
            return CollectionAsync[Properties, References](
                self._connection,
                name,
                properties=data_model_properties,
                references=data_model_references,
                validate_arguments=not skip_argument_validation,
            )
        return Collection[Properties, References](
            self._connection,
            name,
            properties=data_model_properties,
            references=data_model_references,
            validate_arguments=not skip_argument_validation,
        )

    def __create(
        self,
        *,
        config: dict,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Union[
        Collection[Properties, References], Awaitable[CollectionAsync[Properties, References]]
    ]:
        result = self._connection.post(
            path="/schema",
            weaviate_object=config,
            error_msg="Collection may not have been created properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Create collection"),
        )

        if isinstance(result, Awaitable):

            async def execute_():
                res = await result
                collection_name = res.json()["class"]
                collection = self._use(
                    name=collection_name,
                    data_model_properties=data_model_properties,
                    data_model_references=data_model_references,
                    skip_argument_validation=skip_argument_validation,
                )
                assert isinstance(collection, CollectionAsync)
                return collection

            return execute_()

        assert isinstance(result, Response)
        collection_name = result.json()["class"]
        collection = self._use(
            name=collection_name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )
        assert isinstance(collection, Collection)
        return collection

    def __delete(self, *, name: str) -> executor.Result[None]:
        return executor.execute(
            response_callback=lambda res: None,
            method=self._connection.delete,
            path=f"/schema/{name}",
            error_msg="Collection may not have been deleted properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Delete collection"),
        )

    def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        properties: Optional[Sequence[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        reranker_config: Optional[_RerankerProvider] = None,
        sharding_config: Optional[_ShardingConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> executor.Result[
        Union[
            Collection[Properties, References], Awaitable[CollectionAsync[Properties, References]]
        ]
    ]:
        """Use this method to create a collection in Weaviate and immediately return a collection object.

        This method takes several arguments that allow you to configure the collection to your liking. Each argument
        can be produced by using the `Configure` class in `weaviate.classes` to generate the specific configuration
        object that you require given your use case.

        Inspect [the docs](https://weaviate.io/developers/weaviate/configuration) for more information on the different
        configuration options and how they affect the behavior of your collection.

        This method sends a request to Weaviate to create the collection given the configuration. It then returns the newly
        created collection Python object for you to use to make requests.

        Args:
            name: The name of the collection to create.
            description: A description of the collection to create.
            generative_config: The configuration for Weaviate's generative capabilities.
            inverted_index_config: The configuration for Weaviate's inverted index.
            multi_tenancy_config: The configuration for Weaviate's multi-tenancy capabilities.
            properties: The properties of the objects in the collection.
            references: The references of the objects in the collection.
            replication_config: The configuration for Weaviate's replication strategy.
            sharding_config: The configuration for Weaviate's sharding strategy.
            vector_index_config: The configuration for Weaviate's default vector index.
            vectorizer_config: The configuration for Weaviate's default vectorizer or a list of named vectorizers.
            data_model_properties: The generic class that you want to use to represent the properties of objects in this collection. See the `get` method for more information.
            data_model_references: The generic class that you want to use to represent the references of objects in this collection. See the `get` method for more information.
            skip_argument_validation: If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateUnsupportedFeatureError: If the Weaviate version is lower than 1.24.0 and named vectorizers are provided.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        if isinstance(vectorizer_config, list) and self._connection._weaviate_version.is_lower_than(
            1, 24, 0
        ):
            raise WeaviateInvalidInputError(
                "Named vectorizers are only supported in Weaviate v1.24.0 and higher"
            )
        try:
            config = _CollectionConfigCreate(
                description=description,
                generative_config=generative_config,
                inverted_index_config=inverted_index_config,
                multi_tenancy_config=multi_tenancy_config,
                name=name,
                properties=properties,
                references=references,
                replication_config=replication_config,
                reranker_config=reranker_config,
                sharding_config=sharding_config,
                vectorizer_config=vectorizer_config,
                vector_index_config=vector_index_config,
            )
        except ValidationError as e:
            raise WeaviateInvalidInputError(
                f"Invalid collection config create parameters: {e}"
            ) from e

        return self.__create(
            config=config._to_dict(),
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )

    def delete(
        self,
        name: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Use this method to delete collection(s) from the Weaviate instance by its/their name(s).

        WARNING: If you have instances of `client.collections.use()` or `client.collections.create()`
        for these collections within your code, they will cease to function correctly after this operation.

        Args:
            name: The name(s) of the collection(s) to delete.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        _validate_input([_ValidateArgument(expected=[str, List[str]], name="name", value=name)])
        if isinstance(name, str):
            name = _capitalize_first_letter(name)
            if isinstance(self._connection, ConnectionAsync):

                async def _execute() -> None:
                    await executor.aresult(self.__delete(name=name))

                return _execute()
            return executor.result(self.__delete(name=name))
        else:
            if isinstance(self._connection, ConnectionAsync):

                async def _execute() -> None:
                    await asyncio.gather(*[executor.aresult(self.__delete(name=n)) for n in name])

                return _execute()
            for n in name:
                n = _capitalize_first_letter(n)
                executor.result(self.__delete(name=n))
            return None

    def delete_all(self) -> executor.Result[None]:
        """Use this method to delete all collections from the Weaviate instance.

        WARNING: If you have instances of `client.collections.use()` or client.collections.create()
        for these collections within your code, they will cease to function correctly after this operation.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> None:
                collections = (await executor.aresult(self.list_all())).keys()
                await executor.aresult(self.delete(list(collections)))

            return _execute()
        collections = executor.result(self.list_all()).keys()
        return executor.result(self.delete(list(collections)))

    def exists(self, name: str) -> executor.Result[bool]:
        """Use this method to check if a collection exists in the Weaviate instance.

        Args:
            name: The name of the collection to check.

        Returns:
            `True` if the collection exists, `False` otherwise.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        _validate_input([_ValidateArgument(expected=[str], name="name", value=name)])
        path = f"/schema/{_capitalize_first_letter(name)}"

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg="Collection may not exist.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="collection exists"),
        )

    def export_config(
        self,
        name: str,
    ) -> executor.Result[CollectionConfig]:
        """Use this method to export the configuration of a collection from the Weaviate instance.

        Args:            name: The name of the collection to export.

        Returns:
            The configuration of the collection as a `CollectionConfig` object.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        path = f"/schema/{_capitalize_first_letter(name)}"

        def resp(res: Response) -> CollectionConfig:
            data = _decode_json_response_dict(res, "Get schema export")
            assert data is not None
            return _collection_config_from_json(data)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg="Could not export collection config",
        )

    def list_all(
        self,
        simple: bool = True,
    ) -> executor.Result[Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]]:
        """List the configurations of the all the collections currently in the Weaviate instance.

        Args:
            simple: If `True`, return a simplified version of the configuration containing only name and properties.

        Returns:
            A dictionary containing the configurations of all the collections currently in the Weaviate instance mapping
            collection name to collection configuration.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        _validate_input([_ValidateArgument(expected=[bool], name="simple", value=simple)])

        def resp(
            res: Response,
        ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]:
            data = _decode_json_response_dict(res, "Get schema all")
            assert data is not None
            if simple:
                return _collection_configs_simple_from_json(data)
            return _collection_configs_from_json(data)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/schema",
            error_msg="Get all collections",
        )

    def _create_from_dict(
        self,
        config: dict,
    ) -> Union[Collection, Awaitable[CollectionAsync]]:
        return self.__create(config=config)

    def _create_from_config(
        self,
        config: CollectionConfig,
    ) -> executor.Result[Union[Collection, CollectionAsync]]:
        return self._create_from_dict(config=config.to_dict())
