import uuid as uuid_package
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from weaviate.collection.collection_base import CollectionBase, CollectionObjectBase
from weaviate.weaviate_classes import CollectionConfig, MetadataReturn, Metadata, RefToObject
from weaviate.weaviate_types import UUIDS, UUID


@dataclass
class _Object:
    metadata: MetadataReturn
    data: Dict[str, Any]


class CollectionObject(CollectionObjectBase):
    def insert(
        self,
        data: Dict[str, Any],
        uuid: Optional[UUID] = None,
        vector: Optional[List[float]] = None,
    ) -> uuid_package.UUID:
        weaviate_obj: Dict[str, Any] = {
            "class": self._name,
            "properties": {
                key: val if not isinstance(val, RefToObject) else val.to_beacon()
                for key, val in data.items()
            },
        }

        if uuid is not None:
            weaviate_obj["id"] = str(uuid)
        else:
            weaviate_obj["id"] = str(uuid_package.uuid4())

        if vector is not None:
            weaviate_obj["vector"] = vector
        return self._insert(weaviate_obj)

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

    def get_by_id(self, uuid: UUID, metadata: Optional[Metadata]) -> Optional[_Object]:
        ret = self._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return ret
        return self._json_to_object(ret)

    def get(self, metadata: Optional[Metadata] = None) -> List[_Object]:
        ret = self._get(metadata=metadata)
        if ret is None:
            return []

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def reference_add(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self._reference_add(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

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

        return CollectionObject(self._connection, name)

    def get(self, collection_name: str) -> CollectionObject:
        return CollectionObject(self._connection, collection_name)
