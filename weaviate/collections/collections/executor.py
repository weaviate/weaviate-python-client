import asyncio
from typing import (
    Dict,
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
from weaviate.connect.executor import aresult, execute, result, ExecutorResult
from weaviate.connect.v4 import (
    Connection,
    ConnectionAsync,
    _ExpectedStatusCodes,
)
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict
from weaviate.validator import _validate_input, _ValidateArgument

CollectionType = TypeVar("CollectionType", Collection, CollectionAsync)


class _CollectionsExecutor:
    def use(
        self,
        *,
        connection: Connection,
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
        if isinstance(connection, ConnectionAsync):
            return CollectionAsync[Properties, References](
                connection,
                name,
                properties=data_model_properties,
                references=data_model_references,
                validate_arguments=not skip_argument_validation,
            )
        return Collection[Properties, References](
            connection,
            name,
            properties=data_model_properties,
            references=data_model_references,
            validate_arguments=not skip_argument_validation,
        )

    def __create(
        self,
        *,
        connection: Connection,
        config: dict,
    ) -> ExecutorResult[str]:
        def resp(res: Response) -> str:
            collection_name = res.json()["class"]
            assert isinstance(collection_name, str)
            return collection_name

        return execute(
            response_callback=resp,
            method=connection.post,
            path="/schema",
            weaviate_object=config,
            error_msg="Collection may not have been created properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Create collection"),
        )

    def __delete(self, connection: Connection, *, name: str) -> ExecutorResult[None]:
        def resp(res: Response) -> None:
            return None

        return execute(
            response_callback=resp,
            method=connection.delete,
            path=f"/schema/{name}",
            error_msg="Collection may not have been deleted properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Delete collection"),
        )

    def create(
        self,
        name: str,
        *,
        connection: Connection,
        description: Optional[str],
        generative_config: Optional[_GenerativeProvider],
        inverted_index_config: Optional[_InvertedIndexConfigCreate],
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate],
        properties: Optional[Sequence[Property]],
        references: Optional[List[_ReferencePropertyBase]],
        replication_config: Optional[_ReplicationConfigCreate],
        reranker_config: Optional[_RerankerProvider],
        sharding_config: Optional[_ShardingConfigCreate],
        vector_index_config: Optional[_VectorIndexConfigCreate],
        vectorizer_config: Optional[Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]],
        data_model_properties: Optional[Type[Properties]],
        data_model_references: Optional[Type[References]],
        skip_argument_validation: bool = False,
    ) -> ExecutorResult[
        Union[Collection[Properties, References], CollectionAsync[Properties, References]]
    ]:
        if isinstance(vectorizer_config, list) and connection._weaviate_version.is_lower_than(
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

        def resp(
            res: str,
        ) -> Union[Collection[Properties, References], CollectionAsync[Properties, References]]:
            assert (
                config.name == res
            ), f"Name of created collection ({name}) does not match given name ({config.name})"
            return self.use(
                connection=connection,
                name=res,
                data_model_properties=data_model_properties,
                data_model_references=data_model_references,
                skip_argument_validation=skip_argument_validation,
            )

        return execute(
            response_callback=resp,
            method=self.__create,
            connection=connection,
            config=config._to_dict(),
        )

    def delete(
        self, name: Union[str, List[str]], *, connection: Connection
    ) -> ExecutorResult[None]:
        _validate_input([_ValidateArgument(expected=[str, List[str]], name="name", value=name)])
        if isinstance(name, str):
            name = _capitalize_first_letter(name)
            if isinstance(connection, ConnectionAsync):

                async def _execute() -> None:
                    await aresult(self.__delete(connection, name=name))

                return _execute()
            return result(self.__delete(connection, name=name))
        else:
            if isinstance(connection, ConnectionAsync):

                async def _execute() -> None:
                    await asyncio.gather(
                        *[aresult(self.__delete(connection, name=n)) for n in name]
                    )

                return _execute()
            for n in name:
                n = _capitalize_first_letter(n)
                result(self.__delete(connection, name=n))
            return None

    def delete_all(self, *, connection: Connection) -> ExecutorResult[None]:
        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                collections = (await aresult(self.list_all(connection=connection))).keys()
                await aresult(self.delete(list(collections), connection=connection))

            return _execute()
        collections = result(self.list_all(connection=connection)).keys()
        return result(self.delete(list(collections), connection=connection))

    def exists(self, name: str, *, connection: Connection) -> ExecutorResult[bool]:
        _validate_input([_ValidateArgument(expected=[str], name="name", value=name)])
        path = f"/schema/{_capitalize_first_letter(name)}"

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg="Collection may not exist.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="collection exists"),
        )

    def export_config(
        self,
        name: str,
        *,
        connection: Connection,
    ) -> ExecutorResult[CollectionConfig]:
        path = f"/schema/{_capitalize_first_letter(name)}"

        def resp(res: Response) -> CollectionConfig:
            data = _decode_json_response_dict(res, "Get schema export")
            assert data is not None
            return _collection_config_from_json(data)

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg="Could not export collection config",
        )

    def list_all(
        self, simple: bool = True, *, connection: Connection
    ) -> ExecutorResult[Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]]:
        _validate_input([_ValidateArgument(expected=[bool], name="simple", value=simple)])

        def resp(
            res: Response,
        ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]:
            data = _decode_json_response_dict(res, "Get schema all")
            assert data is not None
            if simple:
                return _collection_configs_simple_from_json(data)
            return _collection_configs_from_json(data)

        return execute(
            response_callback=resp,
            method=connection.get,
            path="/schema",
            error_msg="Get all collections",
        )

    def create_from_dict(
        self,
        config: dict,
        *,
        connection: Connection,
    ) -> ExecutorResult[Union[Collection, CollectionAsync]]:
        def resp(res: str) -> Union[Collection, CollectionAsync]:
            return self.use(
                connection=connection,
                name=res,
                data_model_properties=None,
                data_model_references=None,
            )

        return execute(
            response_callback=resp,
            method=self.__create,
            connection=connection,
            config=config,
        )

    def create_from_config(
        self,
        config: CollectionConfig,
        *,
        connection: Connection,
    ) -> ExecutorResult[Union[Collection, CollectionAsync]]:
        return self.create_from_dict(connection=connection, config=config.to_dict())
