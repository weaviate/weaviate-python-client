import datetime
import uuid as uuid_lib
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Union,
    Type,
    TypedDict,
    cast,
    overload,
)

from weaviate.collections.classes.filters import (
    FilterMetadata,
)
from weaviate.collections.classes.grpc import PROPERTIES, REFERENCES, MetadataQuery

from weaviate.collections.classes.internal import (
    _MetadataSingleObjectReturn,
    _ObjectSingleReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    References,
    WeaviateReferences,
    TReferences,
    WeaviateProperties,
    FromNested,
    _Reference,
)
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.queries.base import _BaseQuery
from weaviate.util import _datetime_from_weaviate_str
from weaviate.types import UUID


class _FetchObjectByIDQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _ObjectSingleReturn[Properties, References]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _ObjectSingleReturn[Properties, WeaviateReferences]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _ObjectSingleReturn[Properties, TReferences]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _ObjectSingleReturn[TProperties, References]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _ObjectSingleReturn[TProperties, WeaviateReferences]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _ObjectSingleReturn[TProperties, TReferences]:
        ...

    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Union[
        None,
        _ObjectSingleReturn[Properties, References],
        _ObjectSingleReturn[Properties, WeaviateReferences],
        _ObjectSingleReturn[Properties, TReferences],
        _ObjectSingleReturn[TProperties, References],
        _ObjectSingleReturn[TProperties, WeaviateReferences],
        _ObjectSingleReturn[TProperties, TReferences],
    ]:
        """Retrieve an object from the server by its UUID.

        Arguments:
            `uuid`
                The UUID of the object to retrieve, REQUIRED.
            `include_vector`
                Whether to include the vector in the returned object.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
        if self._is_weaviate_version_123:
            return_metadata = MetadataQuery(
                creation_time_unix=True, last_update_time_unix=True, is_consistent=True
            )
            res = self._query().get(
                limit=1,
                filters=FilterMetadata.ById.equal(uuid),
                return_metadata=self._parse_return_metadata(return_metadata, include_vector),
                return_properties=self._parse_return_properties(return_properties),
                return_references=self._parse_return_references(return_references),
            )
            objects = self._result_to_query_return(
                res,
                _QueryOptions.from_input(
                    return_metadata,
                    return_properties,
                    include_vector,
                    self._references,
                    return_references,
                ),
                return_properties,
                None,
            )

            if len(objects.objects) == 0:
                return None

            obj = objects.objects[0]
            assert obj.metadata is not None
            assert obj.metadata.creation_time_unix is not None
            assert obj.metadata.last_update_time_unix is not None

            return cast(
                Union[
                    None,
                    _ObjectSingleReturn[Properties, References],
                    _ObjectSingleReturn[Properties, WeaviateReferences],
                    _ObjectSingleReturn[Properties, TReferences],
                    _ObjectSingleReturn[TProperties, References],
                    _ObjectSingleReturn[TProperties, WeaviateReferences],
                    _ObjectSingleReturn[TProperties, TReferences],
                ],
                _ObjectSingleReturn(
                    uuid=obj.uuid,
                    vector=obj.vector,
                    properties=obj.properties,
                    metadata=_MetadataSingleObjectReturn(
                        creation_time_unix=obj.metadata.creation_time_unix,
                        last_update_time_unix=obj.metadata.last_update_time_unix,
                        is_consistent=obj.metadata.is_consistent,
                    ),
                    references=obj.references,
                ),
            )
        else:
            return cast(
                Union[
                    None,
                    _ObjectSingleReturn[Properties, References],
                    _ObjectSingleReturn[Properties, WeaviateReferences],
                    _ObjectSingleReturn[Properties, TReferences],
                    _ObjectSingleReturn[TProperties, References],
                    _ObjectSingleReturn[TProperties, WeaviateReferences],
                    _ObjectSingleReturn[TProperties, TReferences],
                ],
                self._get_with_rest(
                    self._name, uuid, include_vector, return_properties, return_references
                ),
            )

    def _get_with_rest(
        self,
        collection: str,
        uuid: UUID,
        include_vector: bool = False,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Optional[_ObjectSingleReturn[Any, Any]]:
        res = self._get_by_id_rest(collection, uuid, include_vector)
        if res is None:
            return None
        else:
            obj_rest = cast(_RestPayload, res)

        parsed_props = self._parse_return_properties(return_properties)
        ret_props = (
            parsed_props
            if isinstance(parsed_props, list) or parsed_props is None
            else [parsed_props]
        )
        props = {}

        def parse_value(value: Any) -> Any:
            if isinstance(value, list):
                return [parse_value(val) for val in value]
            if isinstance(value, str):
                try:
                    return _datetime_from_weaviate_str(value)
                except ValueError:
                    pass
                try:
                    return uuid_lib.UUID(value)
                except ValueError:
                    pass
            return value

        def resolve_nested(obj: Dict[str, WeaviateProperties], prop: FromNested) -> dict:
            nested_props = (
                prop.properties if isinstance(prop.properties, list) else [prop.properties]
            )
            nested = {}
            for nested_prop in nested_props:
                if isinstance(nested_prop, FromNested):
                    return resolve_nested(obj[nested_prop.name], nested_prop)
                else:
                    nested[nested_prop] = parse_value(obj[nested_prop])
            return nested

        if ret_props is not None:
            for prop in ret_props:
                if isinstance(prop, FromNested):
                    props[prop.name] = resolve_nested(obj_rest["properties"], prop)
                else:
                    props[prop] = parse_value(obj_rest["properties"][prop])
        else:
            for key, value in obj_rest["properties"].items():
                if (
                    isinstance(value, list)
                    and len(value) > 0
                    and isinstance(value[0], dict)
                    and "beacon" in value[0]
                ):
                    continue
                else:
                    props[key] = parse_value(value)

        parsed_refs = self._parse_return_references(return_references)
        ret_refs = (
            parsed_refs if isinstance(parsed_refs, list) or parsed_refs is None else [parsed_refs]
        )
        if ret_refs is not None:
            refs = {
                ret_ref.link_on: _Reference._from(
                    [
                        self._get_with_rest(
                            rest_ref["beacon"].split("/")[-2],
                            uuid_lib.UUID(rest_ref["beacon"].split("/")[-1]),
                            ret_ref.include_vector,
                            ret_ref.return_properties,
                            ret_ref.return_references,
                        )  # type: ignore # incompatability between _Object and _ObjectSingleReturn but will remove this anyway in 1.24 and Py GA
                        for rest_ref in cast(
                            List[_RestReference], obj_rest["properties"][ret_ref.link_on]
                        )
                    ]
                )
                for ret_ref in ret_refs
            }
        else:
            refs = None

        return _ObjectSingleReturn(
            uuid=uuid_lib.UUID(obj_rest["id"]),
            vector=obj_rest.get("vector", None),
            properties=props,
            metadata=_MetadataSingleObjectReturn(
                creation_time_unix=datetime.datetime.fromtimestamp(
                    obj_rest["creationTimeUnix"] / 1000, tz=datetime.timezone.utc
                ),
                last_update_time_unix=datetime.datetime.fromtimestamp(
                    obj_rest["lastUpdateTimeUnix"] / 1000, tz=datetime.timezone.utc
                ),
                is_consistent=None,
            ),
            references=refs,
        )


_RestPayload = TypedDict(
    "_RestPayload",
    {
        "class": str,
        "creationTimeUnix": int,
        "id": str,
        "lastUpdateTimeUnix": int,
        "properties": Dict[str, WeaviateProperties],
        "vectorWeights": Optional[List[float]],
        "vector": Optional[List[float]],
    },
)

_RestReference = TypedDict(
    "_RestReference",
    {
        "beacon": str,
        "href": str,
    },
)
