import uuid as uuid_package
from dataclasses import dataclass
from typing import Type, Optional, Any, List, Dict, Generic, Tuple, Union
from pydantic import create_model
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes import (
    BaseProperty,
    BatchReference,
    CollectionModelConfig,
    Errors,
    MetadataGet,
    _MetadataReturn,
    Model,
    UserModelType,
)
from weaviate.collection.collection_base import (
    CollectionBase,
    CollectionObjectBase,
)
from weaviate.collection.grpc import (
    _GRPC,
    GrpcResult,
    HybridFusion,
    PROPERTIES,
    MetadataQuery,
    BM25Options,
    ReturnValues,
    HybridOptions,
    GetOptions,
    NearObjectOptions,
    NearVectorOptions,
)
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _capitalize_first_letter
from weaviate.weaviate_types import UUID, UUIDS, BEACON, PYTHON_TYPE_TO_DATATYPE


@dataclass
class _Object(Generic[Model]):
    data: Model
    metadata: _MetadataReturn


class _Data(Generic[Model]):
    __collection: "CollectionObjectModel[Model]"

    def __init__(self, collection: "CollectionObjectModel[Model]"):
        self.__collection = collection

    def insert(self, obj: Model) -> uuid_package.UUID:
        self.__collection.model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.__collection.name,
            "properties": obj.props_to_dict(),
            "id": str(obj.uuid),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self.__collection._insert(weaviate_obj)
        return uuid_package.UUID(str(obj.uuid))

    def insert_many(self, objects: List[Model]) -> List[Union[uuid_package.UUID, Errors]]:
        for obj in objects:
            self.__collection.model.model_validate(obj)

        weaviate_objs: List[Dict[str, Any]] = [
            {
                "class": self.__collection.name,
                "properties": obj.props_to_dict(),
                "id": str(obj.uuid),
            }
            for obj in objects
        ]
        return self.__collection._insert_many(weaviate_objs)

    def replace(self, obj: Model, uuid: UUID) -> None:
        self.__collection.model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.__collection.name,
            "properties": obj.props_to_dict(),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self.__collection._replace(weaviate_obj, uuid)

    def update(self, obj: Model, uuid: UUID) -> None:
        self.__collection.model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.__collection.name,
            "properties": obj.props_to_dict(update=True),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self.__collection._update(weaviate_obj, uuid)

    def get_by_id(
        self, uuid: UUID, metadata: Optional[MetadataGet] = None
    ) -> Optional[_Object[Model]]:
        ret = self.__collection._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return None
        return self.__collection._json_to_object(ret)

    def get(self, metadata: Optional[MetadataGet] = None) -> Optional[List[_Object[Model]]]:
        ret = self.__collection._get(metadata=metadata)
        if ret is None:
            return None

        return [self.__collection._json_to_object(obj) for obj in ret["objects"]]

    def reference_add(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self.__collection._reference_add(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def reference_delete(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self.__collection._reference_delete(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def reference_replace(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self.__collection._reference_replace(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def reference_add_many(self, from_property: str, refs: List[BatchReference]) -> None:
        refs_dict = [
            {
                "from": BEACON + f"{self.__collection.name}/{ref.from_uuid}/{from_property}",
                "to": BEACON + str(ref.to_uuid),
            }
            for ref in refs
        ]
        self.__collection._reference_add_many(refs_dict)


class _GRPCWrapper(Generic[Model]):
    def __init__(
        self,
        collection: "CollectionObjectModel[Model]",
        connection: Connection,
        model: Type[Model],
    ):
        super().__init__()
        self._model: Type[Model] = model
        self._connection = connection
        self.__non_optional_props = model.get_non_optional_fields(model)
        self.__collection = collection

    def __create_query(self) -> _GRPC:
        return _GRPC(
            self._connection,
            self.__collection.name,
            self.__collection.tenant,
            self.__non_optional_props,
        )

    def get_flat(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().get(
                limit, offset, after, return_metadata, return_properties
            )
        ]

    def get_options(
        self, returns: ReturnValues, options: Optional[GetOptions]
    ) -> List[_Object[Model]]:
        if options is None:
            options = GetOptions()
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().get(
                options.limit, options.offset, options.after, returns.metadata, returns.properties
            )
        ]

    def hybrid_flat(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        objects = self.__create_query().hybrid(
            query,
            alpha,
            vector,
            properties,
            fusion_type,
            limit,
            autocut,
            return_metadata,
            return_properties,
        )
        return [self.__result_to_object(obj) for obj in objects]

    def hybrid_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[HybridOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = HybridOptions()

        objects = self.__create_query().hybrid(
            query,
            options.alpha,
            options.vector,
            options.properties,
            options.fusion_type,
            options.limit,
            options.autocut,
            returns.metadata,
            returns.properties,
        )
        return [self.__result_to_object(obj) for obj in objects]

    def bm25_flat(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().bm25(
                query, properties, limit, autocut, return_metadata, return_properties
            )
        ]

    def bm25_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[BM25Options] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = BM25Options()
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().bm25(
                query,
                options.properties,
                options.limit,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_vector_flat(
        self,
        vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().near_vector(
                vector, certainty, distance, autocut, return_metadata, return_properties
            )
        ]

    def near_vector_options(
        self,
        vector: List[float],
        returns: ReturnValues,
        options: Optional[NearVectorOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearVectorOptions()
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().near_vector(
                vector,
                options.certainty,
                options.distance,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_object_flat(
        self,
        obj: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().near_object(
                obj, certainty, distance, autocut, return_metadata, return_properties
            )
        ]

    def near_object_options(
        self,
        obj: UUID,
        returns: ReturnValues,
        options: Optional[NearObjectOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearObjectOptions()
        return [
            self.__result_to_object(obj)
            for obj in self.__create_query().near_object(
                obj,
                options.certainty,
                options.distance,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def __result_to_object(self, obj: GrpcResult) -> _Object[Model]:
        return _Object[Model](data=self._model(**obj.result), metadata=obj.metadata)


class CollectionObjectModel(CollectionObjectBase, Generic[Model]):
    def __init__(self, connection: Connection, name: str, model: Type[Model]) -> None:
        super().__init__(connection, name)
        self.__model: Type[Model] = model
        self._default_props = model.get_non_optional_fields(model)
        self.data = _Data[Model](self)
        self.query = _GRPCWrapper[Model](self, connection, model)

    @property
    def model(self) -> Type[Model]:
        return self.__model

    def with_tenant(self, tenant: Optional[str] = None) -> "CollectionObjectModel":
        new_collection = self._with_tenant(tenant)
        new_collection.data = _Data(new_collection)
        new_collection.query = _GRPCWrapper(
            new_collection, new_collection._connection, new_collection.__model
        )
        return new_collection

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "CollectionObjectModel":
        return self._with_consistency_level(consistency_level)

    def _json_to_object(self, obj: Dict[str, Any]) -> _Object[Model]:
        for ref in self.__model.get_ref_fields(self.__model):
            if ref not in obj["properties"]:
                continue

            beacons = obj["properties"][ref]
            uuids = []
            for beacon in beacons:
                uri = beacon["beacon"]
                assert isinstance(uri, str)
                uuids.append(uri.split("/")[-1])

            obj["properties"][ref] = uuids

        # weaviate does not save none values, so we need to add them to pass model validation
        for prop in self._default_props:
            if prop not in obj["properties"]:
                obj["properties"][prop] = None

        model_object = _Object[Model](
            data=self.__model(**obj["properties"]), metadata=_MetadataReturn(obj)
        )
        model_object.data.uuid = model_object.metadata.uuid
        model_object.data.vector = model_object.metadata.vector
        return model_object


class CollectionModel(CollectionBase):
    def __init__(self, connection: Connection):
        super().__init__(connection)

    def create(self, config: CollectionModelConfig[Model]) -> CollectionObjectModel[Model]:
        name = super()._create(config)
        if config.name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config.name})"
            )
        return CollectionObjectModel[Model](self._connection, config.name, config.model)

    def get(self, model: Type[Model], name: str) -> CollectionObjectModel[Model]:
        path = f"/schema/{_capitalize_first_letter(name)}"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Schema could not be retrieved.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Get schema", response)

        response_json = response.json()
        model_props = model.type_to_dict(model)
        schema_props = [
            {"name": prop["name"], "dataType": prop["dataType"]}
            for prop in response_json["properties"]
        ]

        def compare(s: List[Any], t: List[Any]) -> bool:
            t = list(t)  # make a mutable copy
            try:
                for elem in s:
                    t.remove(elem)
            except ValueError:
                return False
            return not t

        if compare(model_props, schema_props):
            raise TypeError("Schemas not compatible")
        return CollectionObjectModel[Model](self._connection, name, model)

    def get_dynamic(self, name: str) -> Tuple[CollectionObjectModel[Model], UserModelType]:
        path = f"/schema/{_capitalize_first_letter(name)}"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Schema could not be retrieved.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Get schema", response)

        response_json = response.json()
        fields: Dict[str, Any] = {
            prop["name"]: (PYTHON_TYPE_TO_DATATYPE[prop["dataType"][0]], None)
            for prop in response_json["properties"]
        }
        model = create_model(response_json["class"], **fields, __base__=BaseProperty)

        return CollectionObjectModel(self._connection, name, model), model

    def delete(self, name: str) -> None:
        return self._delete(name)

    def exists(self, name: str) -> bool:
        return self._exists(name)
