import uuid as uuid_package
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from weaviate.collection.collection_base import CollectionBase, CollectionObjectBase
from weaviate.weaviate_types import CollectionConfig, UUID, MetadataReturn, Metadata


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
            "properties": data,
        }

        if uuid is not None:
            weaviate_obj["id"] = str(uuid)

        if vector is not None:
            weaviate_obj["vector"] = vector
        return self._insert(weaviate_obj)

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

    def _json_to_object(self, obj: Dict[str, Any]) -> _Object:
        return _Object(
            data={prop: val for prop, val in obj["properties"].items()},
            metadata=MetadataReturn(**obj),
        )


class Collection(CollectionBase):
    def create(self, config: CollectionConfig) -> CollectionObject:
        super()._create(config)

        return CollectionObject(self._connection, config.name)

    def get(self, collection_name: str) -> CollectionObject:
        return CollectionObject(self._connection, collection_name)
