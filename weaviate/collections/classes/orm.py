# import hashlib
# import uuid as uuid_package
# from dataclasses import dataclass
# from typing import (
#     Any,
#     Dict,
#     Generic,
#     List,
#     Optional,
#     Set,
#     Type,
#     TypeVar,
#     Union,
#     get_args,
#     get_origin,
#     get_type_hints,
#     cast,
# )
# from typing_extensions import is_typeddict

# from pydantic import BaseModel, Field, field_validator
# from pydantic_core import PydanticUndefined

# from weaviate.collections.classes.config import (
#     _CollectionConfigCreateBase,
#     _PropertyConfig,
#     Property,
#     ReferenceProperty,
#     _ReferencePropertyMultiTarget,
#     DataType,
# )
# from weaviate.collections.classes.types import T
# from weaviate.util import _capitalize_first_letter, _to_beacons
# from weaviate.types import PYTHON_TYPE_TO_DATATYPE, UUID

# from weaviate.exceptions import InvalidDataModelException

# from weaviate.collections.classes.internal import References


# @dataclass
# class Reference:
#     ref_type: Union[Type, str]

#     @property
#     def name(self) -> str:
#         if isinstance(self.ref_type, type):
#             return _capitalize_first_letter(self.ref_type.__name__)
#         else:
#             assert isinstance(self.ref_type, str)
#             return _capitalize_first_letter(self.ref_type)


# class BaseProperty(BaseModel):
#     uuid: uuid_package.UUID = Field(default_factory=uuid_package.uuid4)
#     vector: Optional[List[float]] = None

#     def model_post_init(self, __context: Any) -> None:
#         self._reference_fields: Set[str] = self.get_ref_fields(type(self))

#         self._reference_to_class: Dict[str, str] = {}
#         for ref in self._reference_fields:
#             self._reference_to_class[ref] = self.model_fields[ref].metadata[0].name

#     @staticmethod
#     def get_ref_fields(model: Type["BaseProperty"]) -> Set[str]:
#         return {
#             name
#             for name, field in model.model_fields.items()
#             if (
#                 field.metadata is not None
#                 and len(field.metadata) > 0
#                 and isinstance(field.metadata[0], Reference)
#             )
#             and name not in BaseProperty.model_fields
#         }

#     @staticmethod
#     def get_non_ref_fields(model: Type["BaseProperty"]) -> Set[str]:
#         return {
#             name
#             for name, field in model.model_fields.items()
#             if (
#                 field.metadata is None
#                 or len(field.metadata) == 0
#                 or isinstance(field.metadata[0], _PropertyConfig)
#             )
#             and name not in BaseProperty.model_fields
#         }

#     def props_to_dict(self, update: bool = False) -> Dict[str, Any]:
#         fields_to_exclude: Set[str] = self._reference_fields.union({"uuid", "vector"})
#         if update:
#             fields_to_exclude.union(
#                 {field for field in self.model_fields.keys() if field not in self.model_fields_set}
#             )

#         c = self.model_dump(exclude=fields_to_exclude)
#         for ref in self._reference_fields:
#             val = getattr(self, ref, None)
#             if val is not None:
#                 c[ref] = _to_beacons(val, self._reference_to_class[ref])
#         return cast(dict, c)

#     @field_validator("uuid")
#     def create_valid_uuid(cls, input_uuid: UUID) -> uuid_package.UUID:
#         if isinstance(input_uuid, uuid_package.UUID):
#             return input_uuid

#         # see if str is already a valid uuid
#         try:
#             return uuid_package.UUID(input_uuid)
#         except ValueError:
#             hex_string = hashlib.md5(input_uuid.encode("UTF-8")).hexdigest()
#             return uuid_package.UUID(hex=hex_string)

#     @staticmethod
#     def type_to_dict(model: Type["BaseProperty"]) -> List[Dict[str, Any]]:
#         types = get_type_hints(model)

#         non_optional_types = {
#             name: BaseProperty.remove_optional_type(tt)
#             for name, tt in types.items()
#             if name not in BaseProperty.model_fields
#         }

#         non_ref_fields = model.get_non_ref_fields(model)
#         properties = []
#         for name in non_ref_fields:
#             prop = {
#                 "name": name,
#                 "dataType": [PYTHON_TYPE_TO_DATATYPE[non_optional_types[name]]],
#             }
#             metadata_list = model.model_fields[name].metadata
#             if metadata_list is not None and len(metadata_list) > 0:
#                 metadata = metadata_list[0]
#                 if isinstance(metadata, _PropertyConfig):
#                     prop.update(metadata._to_dict())

#             properties.append(prop)

#         reference_fields = model.get_ref_fields(model)
#         properties.extend(
#             {
#                 "name": name,
#                 "dataType": [model.model_fields[name].metadata[0].name],
#             }
#             for name in reference_fields
#         )

#         return properties

#     @staticmethod
#     def type_to_properties(
#         model: Type["BaseProperty"],
#     ) -> List[Union[Property, ReferenceProperty, _ReferencePropertyMultiTarget]]:
#         types = get_type_hints(model)

#         non_optional_types = {
#             name: BaseProperty.remove_optional_type(tt)
#             for name, tt in types.items()
#             if name not in BaseProperty.model_fields
#         }

#         non_ref_fields = model.get_non_ref_fields(model)
#         properties: List[Union[Property, ReferenceProperty, _ReferencePropertyMultiTarget]] = []
#         for name in non_ref_fields:
#             data_type = [PYTHON_TYPE_TO_DATATYPE[non_optional_types[name]]]
#             prop: Dict[str, Any] = {}
#             metadata_list = model.model_fields[name].metadata
#             if metadata_list is not None and len(metadata_list) > 0:
#                 metadata = metadata_list[0]
#                 if isinstance(metadata, _PropertyConfig):
#                     prop.update(metadata._to_dict())

#             properties.append(Property(name=name, data_type=DataType(data_type[0]), **prop))

#         reference_fields = model.get_ref_fields(model)
#         properties.extend(
#             ReferenceProperty(
#                 name=name,
#                 target_collection=model.model_fields[name].metadata[0].name,
#             )
#             for name in reference_fields
#         )

#         return properties

#     @staticmethod
#     def get_non_default_fields(model: Type["BaseProperty"]) -> Set[str]:
#         return {
#             field
#             for field, val in model.model_fields.items()
#             if val.default == PydanticUndefined and field not in BaseProperty.model_fields.keys()
#         }

#     @staticmethod
#     def remove_optional_type(python_type: T) -> Union[Any, List[Any], T]:
#         args = get_args(python_type)
#         if len(args) == 0:
#             return python_type

#         return_type = [t for t in args if t is not None][0]

#         is_list = get_origin(python_type) == list
#         if is_list:
#             return List[return_type]  # type: ignore
#         else:
#             return return_type


# Model = TypeVar("Model", bound=BaseProperty)


# class RefToObjectModel(BaseModel, Generic[Model]):
#     uuids_to: Union[List[UUID], UUID] = Field()

#     def to_beacon(self) -> List[Dict[str, str]]:
#         return _to_beacons(self.uuids_to)


# UserModelType = Type[BaseProperty]


# class CollectionModelConfig(_CollectionConfigCreateBase, Generic[Model]):
#     model: Type[Model]

#     def _to_dict(self) -> Dict[str, Any]:
#         ret_dict = super()._to_dict()

#         ret_dict["class"] = _capitalize_first_letter(self.model.__name__)

#         if self.model is not None:
#             ret_dict["properties"] = self.model.type_to_dict(self.model)

#         return ret_dict
