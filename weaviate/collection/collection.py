from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union, Tuple

import uuid as uuid_package

from weaviate.collection.collection_base import CollectionBase, CollectionObjectBase
from weaviate.collection.collection_classes import Errors
from weaviate.collection.grpc import GrpcBuilderBase, HybridFusion, ReturnValues
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.weaviate_classes import CollectionConfig, MetadataReturn, Metadata, RefToObject
from weaviate.weaviate_types import UUIDS, UUID, BEACON


@dataclass
class _Object:
    metadata: MetadataReturn
    data: Dict[str, Any]


@dataclass
class DataObject:
    data: Dict[str, Any]
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None


@dataclass
class BatchReference:
    from_uuid: UUID
    to_uuid: UUID


class GrpcBuilder(GrpcBuilderBase):
    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
    ) -> List[_Object]:
        return [self.__dict_to_obj(obj) for obj in self._get(limit, offset, after)]

    def hybrid(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
    ) -> List[_Object]:
        objects = self._hybrid(query, alpha, vector, properties, fusion_type, limit, autocut)
        return [self.__dict_to_obj(obj) for obj in objects]

    def bm25(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
    ) -> List[_Object]:
        return [self.__dict_to_obj(obj) for obj in self._bm25(query, properties, limit, autocut)]

    def near_vector(
        self,
        vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
    ) -> List[_Object]:
        return [
            self.__dict_to_obj(obj)
            for obj in self._near_vector(vector, certainty, distance, autocut)
        ]

    def near_object(
        self,
        obj: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
    ) -> List[_Object]:
        return [
            self.__dict_to_obj(obj) for obj in self._near_object(obj, certainty, distance, autocut)
        ]

    def __dict_to_obj(self, obj: Tuple[Dict[str, Any], MetadataReturn]) -> _Object:
        data: Dict[str, Any] = obj[0]
        for key in data.keys():
            if isinstance(data[key], List):
                for i, _ in enumerate(data[key]):
                    data[key][i] = self.__dict_to_obj(data[key][i])

        return _Object(data=data, metadata=obj[1])


class CollectionObject(CollectionObjectBase):
    @dataclass
    class __Data:
        collection: "CollectionObject"

        def insert(
            self,
            data: Dict[str, Any],
            uuid: Optional[UUID] = None,
            vector: Optional[List[float]] = None,
        ) -> uuid_package.UUID:
            weaviate_obj: Dict[str, Any] = {
                "class": self.collection._name,
                "properties": {
                    key: val if not isinstance(val, RefToObject) else val.to_beacon()
                    for key, val in data.items()
                },
                "id": str(uuid if uuid is not None else uuid_package.uuid4()),
            }

            if vector is not None:
                weaviate_obj["vector"] = vector

            return self.collection._insert(weaviate_obj)

    def __init__(self, connection: Connection, name: str) -> None:
        super().__init__(connection, name)
        self.data = self.__Data(self)

    def with_tenant(self, tenant: Optional[str] = None) -> "CollectionObject":
        return self._with_tenant(tenant)

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "CollectionObject":
        return self._with_consistency_level(consistency_level)

    def insert_many(self, objects: List[DataObject]) -> List[Union[uuid_package.UUID, Errors]]:
        weaviate_objs: List[Dict[str, Any]] = [
            {
                "class": self._name,
                "properties": {
                    key: val if not isinstance(val, RefToObject) else val.to_beacon()
                    for key, val in obj.data.items()
                },
                "id": str(obj.uuid) if obj.uuid is not None else str(uuid_package.uuid4()),
            }
            for obj in objects
        ]

        return self._insert_many(weaviate_objs)

    def replace(
        self, data: Dict[str, Any], uuid: UUID, vector: Optional[List[float]] = None
    ) -> None:
        weaviate_obj: Dict[str, Any] = {
            "class": self._name,
            "properties": {
                key: val if not isinstance(val, RefToObject) else val.to_beacon()
                for key, val in data.items()
            },
        }
        if vector is not None:
            weaviate_obj["vector"] = vector

        self._replace(weaviate_obj, uuid=uuid)

    def update(
        self, data: Dict[str, Any], uuid: UUID, vector: Optional[List[float]] = None
    ) -> None:
        weaviate_obj: Dict[str, Any] = {
            "class": self._name,
            "properties": {
                key: val if not isinstance(val, RefToObject) else val.to_beacon()
                for key, val in data.items()
            },
        }
        if vector is not None:
            weaviate_obj["vector"] = vector

        self._update(weaviate_obj, uuid=uuid)

    def get_by_id(self, uuid: UUID, metadata: Optional[Metadata] = None) -> Optional[_Object]:
        ret = self._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return ret
        return self._json_to_object(ret)

    def get(self, metadata: Optional[Metadata] = None) -> List[_Object]:
        ret = self._get(metadata=metadata)
        if ret is None:
            return []

        return [self._json_to_object(obj) for obj in ret["objects"]]

    @property
    def get_grpc(self) -> ReturnValues[GrpcBuilder]:
        return ReturnValues[GrpcBuilder](GrpcBuilder(self._connection, self._name))

    def reference_add(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self._reference_add(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def reference_batch_add(self, from_property: str, refs: List[BatchReference]) -> None:
        refs_dict = [
            {
                "from": BEACON + f"{self._name}/{ref.from_uuid}/{from_property}",
                "to": BEACON + str(ref.to_uuid),
            }
            for ref in refs
        ]
        self._reference_batch_add(refs_dict)

    def reference_delete(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self._reference_delete(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def reference_replace(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self._reference_replace(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def _json_to_object(self, obj: Dict[str, Any]) -> _Object:
        return _Object(
            data={prop: val for prop, val in obj["properties"].items()},
            metadata=MetadataReturn(**obj),
        )


class Collection(CollectionBase):
    def create(self, config: CollectionConfig) -> CollectionObject:
        name = super()._create(config)
        if config.name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config.name})"
            )
        return CollectionObject(self._connection, config.name)

    def get(self, name: str) -> CollectionObject:
        return CollectionObject(self._connection, name)

    def delete(self, name: str) -> None:
        self._delete(name)

    def exists(self, name: str) -> bool:
        return self._exists(name)
