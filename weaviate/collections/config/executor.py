import asyncio
from typing import Dict, Any, List, Literal, Optional, Tuple, Union, cast

from httpx import Response
from pydantic_core import ValidationError

from weaviate.collections.classes.config import (
    _CollectionConfigUpdate,
    _InvertedIndexConfigUpdate,
    _ReplicationConfigUpdate,
    _VectorIndexConfigFlatUpdate,
    PropertyType,
    Property,
    ReferenceProperty,
    _ReferencePropertyMultiTarget,
    _VectorIndexConfigHNSWUpdate,
    CollectionConfig,
    CollectionConfigSimple,
    ShardStatus,
    _ShardStatus,
    ShardTypes,
    _NamedVectorConfigUpdate,
    _MultiTenancyConfigUpdate,
    _GenerativeProvider,
    _RerankerProvider,
)
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_config_simple_from_json,
)
from weaviate.collections.classes.config_vector_index import _VectorIndexConfigDynamicUpdate
from weaviate.connect.executor import aresult, execute, result, ExecutorResult
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, Connection
from weaviate.exceptions import (
    WeaviateInvalidInputError,
)
from weaviate.util import _decode_json_response_dict, _decode_json_response_list, _ServerVersion
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings


class _ConfigExecutor:
    def __init__(
        self,
        weaviate_version: _ServerVersion,
        name: str,
        tenant: Optional[str] = None,
    ) -> None:
        self.__weaviate_version = weaviate_version
        self.__name = name
        self.__tenant = tenant

    def __get(self, connection: Connection) -> ExecutorResult[Dict[str, Any]]:
        def resp(res: Response) -> Dict[str, Any]:
            return cast(Dict[str, Any], res.json())

        return execute(
            response_callback=resp,
            method=connection.get,
            path=f"/schema/{self.__name}",
            error_msg="Collection configuration could not be retrieved.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Get collection configuration"),
        )

    def get(
        self, simple: bool = False, *, connection: Connection
    ) -> ExecutorResult[Union[CollectionConfig, CollectionConfigSimple]]:
        _validate_input([_ValidateArgument(expected=[bool], name="simple", value=simple)])

        def resp(res: Dict[str, Any]) -> Union[CollectionConfig, CollectionConfigSimple]:
            if simple:
                return _collection_config_simple_from_json(res)
            return _collection_config_from_json(res)

        return execute(
            response_callback=resp,
            method=self.__get,
            connection=connection,
        )

    def update(
        self,
        *,
        description: Optional[str] = None,
        property_descriptions: Optional[Dict[str, str]] = None,
        inverted_index_config: Optional[_InvertedIndexConfigUpdate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigUpdate] = None,
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
            ]
        ] = None,
        vectorizer_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigDynamicUpdate,
                List[_NamedVectorConfigUpdate],
            ]
        ] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        reranker_config: Optional[_RerankerProvider] = None,
        connection: Connection,
    ) -> ExecutorResult[None]:
        if vector_index_config is not None:
            _Warnings.vector_index_config_in_config_update()
        try:
            config = _CollectionConfigUpdate(
                description=description,
                property_descriptions=property_descriptions,
                inverted_index_config=inverted_index_config,
                replication_config=replication_config,
                vector_index_config=vector_index_config,
                vectorizer_config=vectorizer_config,
                multi_tenancy_config=multi_tenancy_config,
                generative_config=generative_config,
                reranker_config=reranker_config,
            )
        except ValidationError as e:
            raise WeaviateInvalidInputError("Invalid collection config update parameters.") from e

        def resp(schema: Dict[str, Any]) -> ExecutorResult[None]:
            schema = config.merge_with_existing(schema)

            def inner_resp(res: Response) -> None:
                return None

            return execute(
                response_callback=inner_resp,
                method=connection.put,
                path=f"/schema/{self.__name}",
                weaviate_object=schema,
                error_msg="Collection configuration may not have been updated.",
                status_codes=_ExpectedStatusCodes(
                    ok_in=200, error="Update collection configuration"
                ),
            )

        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                schema = await aresult(self.__get(connection=connection))
                return await aresult(resp(schema))

            return _execute()
        schema = result(self.__get(connection=connection))
        return result(resp(schema))

    def __add_property(
        self, connection: Connection, *, additional_property: PropertyType
    ) -> ExecutorResult[None]:
        path = f"/schema/{self.__name}/properties"
        obj = additional_property._to_dict()

        def resp(schema: Dict[str, Any]) -> ExecutorResult[None]:
            if schema.get("moduleConfig"):
                configured_module = list(schema.get("moduleConfig", {}).keys())[0]
                modconf = {}
                if "skip_vectorization" in obj:
                    modconf["skip"] = obj["skip_vectorization"]
                    del obj["skip_vectorization"]

                if "vectorize_property_name" in obj:
                    modconf["vectorizePropertyName"] = obj["vectorize_property_name"]
                    del obj["vectorize_property_name"]

                if len(modconf) > 0:
                    obj["moduleConfig"] = {configured_module: modconf}

            def inner_resp(res: Response) -> None:
                return None

            return execute(
                response_callback=inner_resp,
                method=connection.post,
                path=path,
                weaviate_object=obj,
                error_msg="Property may not have been added properly.",
                status_codes=_ExpectedStatusCodes(ok_in=200, error="Add property to collection"),
            )

        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                schema = await aresult(self.__get(connection=connection))
                return await aresult(resp(schema))

            return _execute()
        schema = result(self.__get(connection=connection))
        return result(resp(schema))

    def __property_exists(
        self, connection: Connection, *, property_name: str
    ) -> ExecutorResult[bool]:
        def resp(schema: Dict[str, Any]) -> bool:
            conf = _collection_config_simple_from_json(schema)
            if len(conf.properties) == 0:
                return False
            for prop in conf.properties:
                if prop.name == property_name:
                    return True
            return False

        return execute(
            response_callback=resp,
            method=self.__get,
            connection=connection,
        )

    def __reference_exists(
        self, connection: Connection, *, reference_name: str
    ) -> ExecutorResult[bool]:
        def resp(schema: Dict[str, Any]) -> bool:
            conf = _collection_config_simple_from_json(schema)
            if len(conf.references) == 0:
                return False
            for ref in conf.references:
                if ref.name == reference_name:
                    return True
            return False

        return execute(
            response_callback=resp,
            method=self.__get,
            connection=connection,
        )

    def __get_shards(self, connection: Connection) -> ExecutorResult[List[ShardStatus]]:
        def resp(res: Response) -> List[ShardStatus]:
            shards = _decode_json_response_list(res, "get shards")
            assert shards is not None
            return [
                _ShardStatus(
                    name=shard["name"],
                    status=shard["status"],
                    vector_queue_size=shard["vectorQueueSize"],
                )
                for shard in shards
            ]

        return execute(
            response_callback=resp,
            method=connection.get,
            path=f"/schema/{self.__name}/shards{f'?tenant={self.__tenant}' if self.__tenant else ''}",
            error_msg="Shard statuses could not be retrieved.",
        )

    def get_shards(self, connection: Connection) -> ExecutorResult[List[ShardStatus]]:
        return self.__get_shards(connection)

    def __update_shard(
        self, connection: Connection, *, shard_name: str, status: str
    ) -> ExecutorResult[Tuple[str, ShardTypes]]:
        path = f"/schema/{self.__name}/shards/{shard_name}"
        data = {"status": status}

        def resp(res: Response) -> Tuple[str, ShardTypes]:
            shard = _decode_json_response_dict(res, f"Update shard '{shard_name}' status")
            assert shard is not None
            return shard_name, shard["status"]

        return execute(
            response_callback=resp,
            method=connection.put,
            path=path,
            weaviate_object=data,
            error_msg=f"shard '{shard_name}' may not have been updated.",
        )

    def update_shards(
        self,
        status: Literal["READY", "READONLY"],
        shard_names: Optional[Union[str, List[str]]] = None,
        *,
        connection: Connection,
    ) -> ExecutorResult[Dict[str, ShardTypes]]:
        if isinstance(connection, ConnectionAsync):

            async def _execute(
                shard_names: Optional[Union[str, List[str]]]
            ) -> Dict[str, ShardTypes]:
                if shard_names is None:
                    shards_config = await aresult(self.__get_shards(connection=connection))
                    shard_names = [shard_config.name for shard_config in shards_config]
                elif isinstance(shard_names, str):
                    shard_names = [shard_names]

                results = await asyncio.gather(
                    *[
                        aresult(
                            self.__update_shard(
                                connection=connection, shard_name=shard_name, status=status
                            )
                        )
                        for shard_name in shard_names
                    ]
                )

                return {result[0]: result[1] for result in results}

            return _execute(shard_names)

        if shard_names is None:
            shards_config = result(self.__get_shards(connection=connection))
            shard_names = [shard_config.name for shard_config in shards_config]
        elif isinstance(shard_names, str):
            shard_names = [shard_names]

        return {
            result[0]: result[1]
            for result in [
                result(
                    self.__update_shard(connection=connection, shard_name=shard_name, status=status)
                )
                for shard_name in shard_names
            ]
        }

    def add_property(self, prop: Property, *, connection: Connection) -> ExecutorResult[None]:
        _validate_input([_ValidateArgument(expected=[Property], name="prop", value=prop)])

        def resp(exists: bool) -> ExecutorResult[None]:
            if exists:
                raise WeaviateInvalidInputError(
                    f"Property with name '{prop.name}' already exists in collection '{self.__name}'."
                )
            return self.__add_property(connection=connection, additional_property=prop)

        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                exists = await aresult(
                    self.__property_exists(connection=connection, property_name=prop.name)
                )
                return await aresult(resp(exists))

            return _execute()
        exists = result(self.__property_exists(connection=connection, property_name=prop.name))
        return result(resp(exists))

    def add_reference(
        self,
        ref: Union[ReferenceProperty, _ReferencePropertyMultiTarget],
        *,
        connection: Connection,
    ) -> ExecutorResult[None]:
        _validate_input(
            [
                _ValidateArgument(
                    expected=[ReferenceProperty, _ReferencePropertyMultiTarget],
                    name="ref",
                    value=ref,
                )
            ]
        )

        def resp(exists: bool) -> ExecutorResult[None]:
            if exists:
                raise WeaviateInvalidInputError(
                    f"Reference with name '{ref.name}' already exists in collection '{self.__name}'."
                )
            return self.__add_property(connection=connection, additional_property=ref)

        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                exists = await aresult(
                    self.__reference_exists(connection=connection, reference_name=ref.name)
                )
                return await aresult(resp(exists))

            return _execute()
        exists = result(self.__reference_exists(connection=connection, reference_name=ref.name))
        return result(resp(exists))
