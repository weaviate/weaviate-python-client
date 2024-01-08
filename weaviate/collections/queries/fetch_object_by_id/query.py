import datetime
import uuid as uuid_lib
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Union,
    TypedDict,
    cast,
)

from weaviate.collections.classes.filters import (
    FilterMetadata,
)
from weaviate.collections.classes.grpc import MetadataQuery
from weaviate.collections.classes.internal import (
    _ObjectSingleReturn,
    _MetadataSingleObjectReturn,
    QuerySingleReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    References,
    TReferences,
    WeaviateProperties,
    FromNested,
    CrossReferences,
    _CrossReference,
)
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.queries.base import _BaseQuery
from weaviate.types import UUID
from weaviate.util import _datetime_from_weaviate_str


class _FetchObjectByIDQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Optional[QuerySingleReturn]:
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

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided.
            - If `return_references` is not provided then no references are provided.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
        if self._is_weaviate_version_123:
            return_metadata = MetadataQuery(
                creation_time=True, last_update_time=True, is_consistent=True
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
            assert obj.metadata.creation_time is not None
            assert obj.metadata.last_update_time is not None

            return cast(
                Union[
                    None,
                    _ObjectSingleReturn[Properties, References],
                    _ObjectSingleReturn[Properties, CrossReferences],
                    _ObjectSingleReturn[Properties, TReferences],
                    _ObjectSingleReturn[TProperties, References],
                    _ObjectSingleReturn[TProperties, CrossReferences],
                    _ObjectSingleReturn[TProperties, TReferences],
                ],
                _ObjectSingleReturn(
                    uuid=obj.uuid,
                    vector=obj.vector,
                    properties=obj.properties,
                    metadata=_MetadataSingleObjectReturn(
                        creation_time=obj.metadata.creation_time,
                        last_update_time=obj.metadata.last_update_time,
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
                    _ObjectSingleReturn[Properties, CrossReferences],
                    _ObjectSingleReturn[Properties, TReferences],
                    _ObjectSingleReturn[TProperties, References],
                    _ObjectSingleReturn[TProperties, CrossReferences],
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
            if isinstance(value, dict):
                return {key: parse_value(val) for key, val in value.items()}
            return value

        def resolve_nested(obj: Any, prop: FromNested) -> dict:
            assert isinstance(obj, dict)
            nested_props = (
                prop.properties if isinstance(prop.properties, list) else [prop.properties]
            )
            nested: Dict[str, Any] = {}
            for nested_prop in nested_props:
                if isinstance(nested_prop, FromNested):
                    val = obj[nested_prop.name]
                    if isinstance(val, list):
                        nested[nested_prop.name] = [resolve_nested(o, nested_prop) for o in val]
                    else:
                        nested[nested_prop.name] = resolve_nested(val, nested_prop)
                else:
                    nested[nested_prop] = parse_value(obj[nested_prop])
            return nested

        if ret_props is not None:
            for prop in ret_props:
                if isinstance(prop, FromNested):
                    props[prop.name] = resolve_nested(obj_rest["properties"][prop.name], prop)
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
        refs: Optional[dict] = None
        if ret_refs is not None:
            refs = {
                ret_ref.link_on: _CrossReference._from(
                    [
                        self._get_with_rest(
                            rest_ref["beacon"].split("/")[-2],
                            uuid_lib.UUID(rest_ref["beacon"].split("/")[-1]),
                            ret_ref.include_vector,
                            ret_ref.return_properties,
                            ret_ref.return_references,
                        )  # type: ignore
                        for rest_ref in cast(
                            List[_RestReference], obj_rest["properties"][ret_ref.link_on]
                        )
                    ]
                )
                for ret_ref in ret_refs
                if obj_rest["properties"].get(ret_ref.link_on) is not None
            }
            if all(ref is None for ref in refs.values()):
                refs = None

        return _ObjectSingleReturn(
            uuid=uuid_lib.UUID(obj_rest["id"]),
            vector=obj_rest.get("vector", None),
            properties=props,
            metadata=_MetadataSingleObjectReturn(
                creation_time=datetime.datetime.fromtimestamp(
                    obj_rest["creationTimeUnix"] / 1000, tz=datetime.timezone.utc
                ),
                last_update_time=datetime.datetime.fromtimestamp(
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
