# ORM API is not yet supported

# from typing import Type, Optional, Any, Dict, Generic, Tuple

# from pydantic import create_model

# from weaviate.collections.base import _CollectionBase, _CollectionsBase
# from weaviate.collections.classes.config import ConsistencyLevel
# from weaviate.collections.classes.orm import (
#     BaseProperty,
#     CollectionModelConfig,
#     Model,
#     UserModelType,
# )
# from weaviate.collections.config import _ConfigCollectionModel
# from weaviate.collections.data import _DataCollectionModel

# # from weaviate.collections.query import _GrpcCollectionModel
# from weaviate.collections.tenants import _Tenants
# from weaviate.connect import ConnectionV4
# from weaviate.exceptions import UnexpectedStatusCodeError
# from weaviate.util import _capitalize_first_letter
# from weaviate.types import PYTHON_TYPE_TO_DATATYPE


# class _CollectionObjectModel(_CollectionBase, Generic[Model]):
#     def __init__(
#         self,
#         connection: ConnectionV4,
#         name: str,
#         model: Type[Model],
#         config: _ConfigCollectionModel,
#         consistency_level: Optional[ConsistencyLevel] = None,
#         tenant: Optional[str] = None,
#     ) -> None:
#         super().__init__(connection, name)

#         self.config = config
#         self.data = _DataCollectionModel[Model](
#             connection, self.name, model, consistency_level, tenant
#         )
#         # self.query = _GrpcCollectionModel[Model](
#         #     connection, self.name, model, tenant, consistency_level
#         # )
#         self.tenants = _Tenants(connection, self.name)

#         self.__consistency_level = consistency_level
#         self.__model: Type[Model] = model
#         self.__tenant = tenant

#     @property
#     def model(self) -> Type[Model]:
#         return self.__model

#     def with_tenant(self, tenant: Optional[str] = None) -> "_CollectionObjectModel[Model]":
#         return _CollectionObjectModel[Model](
#             self._connection, self.name, self.__model, self.config, self.__consistency_level, tenant
#         )

#     def with_consistency_level(
#         self, consistency_level: Optional[ConsistencyLevel] = None
#     ) -> "_CollectionObjectModel[Model]":
#         return _CollectionObjectModel[Model](
#             self._connection, self.name, self.__model, self.config, consistency_level, self.__tenant
#         )


# class _CollectionModel(_CollectionsBase):
#     def create(self, config: CollectionModelConfig[Model]) -> _CollectionObjectModel[Model]:
#         name = super()._create(config._to_dict())
#         config_name = _capitalize_first_letter(config.model.__name__)
#         if config_name != name:
#             raise ValueError(
#                 f"Name of created collection ({name}) does not match given name ({config_name})"
#             )
#         return self.get(config.model)

#     def get(self, model: Type[Model]) -> _CollectionObjectModel[Model]:
#         name = _capitalize_first_letter(model.__name__)
#         config = _ConfigCollectionModel(self._connection, name, None)
#         if config.is_invalid(model):
#             raise TypeError(
#                 f"Model {model.__name__} definition does not match collection {name} config"
#             )
#         return _CollectionObjectModel[Model](self._connection, name, model, config)

#     def get_dynamic(self, name: str) -> Tuple[_CollectionObjectModel[BaseProperty], UserModelType]:
#         path = f"/schema/{_capitalize_first_letter(name)}"

#         response = self._connection.get(path=path, error_msg="Collection could not be retrieved.")
#         if response.status_code != 200:
#             raise UnexpectedStatusCodeError("Get schema", response)

#         response_json = response.json()
#         fields: Dict[str, Any] = {
#             prop["name"]: (PYTHON_TYPE_TO_DATATYPE[prop["dataType"][0]], None)
#             for prop in response_json["properties"]
#         }
#         model = create_model(response_json["class"], **fields, __base__=BaseProperty)
#         config = _ConfigCollectionModel(self._connection, name, None)
#         return _CollectionObjectModel[BaseProperty](self._connection, name, model, config), model

#     def delete(self, model: Type[Model]) -> None:
#         """Use this method to delete a collection from the Weaviate instance by its ORM model.

#         WARNING: If you have instances of client.orm.get() or client.orm.create()
#         for this collection within your code, they will cease to function correctly after this operation.

#         Parameters:
#             - model: The ORM model of the collection to be deleted.
#         """
#         name = _capitalize_first_letter(model.__name__)
#         return self._delete(name)

#     def exists(self, model: Type[Model]) -> bool:
#         name = _capitalize_first_letter(model.__name__)
#         return self._exists(name)

#     def update(self, model: Type[Model]) -> _CollectionObjectModel[Model]:
#         name = _capitalize_first_letter(model.__name__)
#         config = _ConfigCollectionModel(self._connection, name, None)
#         config.update_model(model)
#         return _CollectionObjectModel[Model](self._connection, name, model, config)

# class _DataCollectionModel(Generic[Model], _Data):
#     def __init__(
#         self,
#         connection: ConnectionV4,
#         name: str,
#         model: Type[Model],
#         consistency_level: Optional[ConsistencyLevel],
#         tenant: Optional[str],
#     ):
#         super().__init__(connection, name, consistency_level, tenant)
#         self.__model = model

#     def _json_to_object(self, obj: Dict[str, Any]) -> Object[Model, dict]:
#         for ref in self.__model.get_ref_fields(self.__model):
#             if ref not in obj["properties"]:
#                 continue

#             beacons = obj["properties"][ref]
#             uuids = []
#             for beacon in beacons:
#                 uri = beacon["beacon"]
#                 assert isinstance(uri, str)
#                 uuids.append(uri.split("/")[-1])

#             obj["properties"][ref] = uuids

#         # weaviate does not save none values, so we need to add them to pass model validation
#         for prop in self.__model.get_non_default_fields(self.__model):
#             if prop not in obj["properties"]:
#                 obj["properties"][prop] = None

#         # uuid, vector, metadata = _metadata_from_dict(obj)
#         uuid = uuid_package.uuid4()
#         metadata = MetadataReturn()
#         model_object = Object[Model, dict](
#             collection=self.name,
#             properties=self.__model.model_validate(
#                 {
#                     **obj["properties"],
#                     # "uuid": uuid,
#                     # "vector": vector,
#                 }
#             ),
#             references={},
#             metadata=metadata,
#             uuid=uuid,
#             vector=None,
#         )
#         return model_object

#     def insert(self, obj: Model) -> uuid_package.UUID:
#         self.__model.model_validate(obj)
#         weaviate_obj: Dict[str, Any] = {
#             "class": self.name,
#             "properties": self._serialize_props(obj.props_to_dict()),
#             "id": str(obj.uuid),
#         }
#         if obj.vector is not None:
#             weaviate_obj["vector"] = obj.vector

#         self._insert(weaviate_obj)
#         return uuid_package.UUID(str(obj.uuid))

#     def insert_many(self, objects: List[Model]) -> BatchObjectReturn:
#         for obj in objects:
#             self.__model.model_validate(obj)

#         data_objects = [
#             _BatchObject(
#                 collection=self.name,
#                 properties=obj.props_to_dict(),
#                 tenant=self._tenant,
#                 uuid=obj.uuid,
#                 vector=obj.vector,
#                 references=None,
#             )
#             for obj in objects
#         ]

#         return self._batch_grpc.objects(data_objects, self._connection.timeout_config.connect)

#     def replace(self, obj: Model, uuid: UUID) -> None:
#         self.__model.model_validate(obj)

#         weaviate_obj: Dict[str, Any] = {
#             "class": self.name,
#             "properties": self._serialize_props(obj.props_to_dict()),
#         }
#         if obj.vector is not None:
#             weaviate_obj["vector"] = obj.vector

#         self._replace(weaviate_obj, uuid)

#     def update(self, obj: Model, uuid: UUID) -> None:
#         self.__model.model_validate(obj)

#         weaviate_obj: Dict[str, Any] = {
#             "class": self.name,
#             "properties": self._serialize_props(obj.props_to_dict()),
#         }
#         if obj.vector is not None:
#             weaviate_obj["vector"] = obj.vector

#         self._update(weaviate_obj, uuid)

#     def reference_add(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
#         self._reference_add(from_uuid=from_uuid, from_property=from_property, ref=ref)

#     def reference_delete(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
#         self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

#     def reference_replace(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
#         self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)

#     def reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn:
#         return self._reference_add_many(refs)

# class _ConfigCollectionModel(_ConfigBase):
#     def __compare_properties_with_model(
#         self, schema_props: List[_Property], model_props: List[PropertyType]
#     ) -> Tuple[List[_Property], List[PropertyType]]:
#         only_in_model: List[PropertyType] = []
#         only_in_schema: List[_Property] = list(schema_props)

#         schema_props_simple = [
#             {
#                 "name": prop.name,
#                 "dataType": prop.to_dict().get("dataType"),
#             }
#             for prop in schema_props
#         ]

#         for prop in model_props:
#             try:
#                 idx = schema_props_simple.index(
#                     {"name": prop.name, "dataType": prop._to_dict().get("dataType")}
#                 )
#                 schema_props_simple.pop(idx)
#                 only_in_schema.pop(idx)
#             except ValueError:
#                 only_in_model.append(prop)
#         return only_in_schema, only_in_model

#     def update_model(self, model: Type[Model]) -> None:
#         only_in_schema, only_in_model = self.__compare_properties_with_model(
#             self.get().properties, model.type_to_properties(model)
#         )
#         if len(only_in_schema) > 0:
#             raise TypeError("Schema has extra properties")

#         # we can only allow new optional types unless the default is None
#         for prop in only_in_model:
#             new_field = model.model_fields[prop.name]
#             if new_field.annotation is None:
#                 continue  # if user did not annotate with type then ignore field
#             non_optional_type = model.remove_optional_type(new_field.annotation)
#             if new_field.default is not None and non_optional_type == new_field.annotation:
#                 raise WeaviateAddInvalidPropertyError(prop.name)

#         for prop in only_in_model:
#             self._add_property(prop)

#     def is_invalid(self, model: Type[Model]) -> bool:
#         only_in_schema, only_in_model = self.__compare_properties_with_model(
#             self.get().properties, model.type_to_properties(model)
#         )
#         return len(only_in_schema) > 0 or len(only_in_model) > 0
