from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, cast

from pydantic import BaseModel, ConfigDict, Field


class _ConfigCreateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def _to_dict(self) -> Dict[str, Any]:
        return cast(dict, self.model_dump(exclude_none=True))


class _ConfigUpdateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if val is None:
                continue
            if isinstance(val, Enum):
                schema[cls_field] = str(val.value)
            elif isinstance(val, (int, float, bool, str, list)):
                schema[cls_field] = val
            elif isinstance(val, _QuantizerConfigUpdate):
                quantizers = ["pq", "bq", "sq"]
                schema[val.quantizer_name()] = val.merge_with_existing(schema[val.quantizer_name()])
                for quantizer in quantizers:
                    if quantizer == val.quantizer_name() or quantizer not in schema:
                        continue
                    assert (
                        "enabled" in schema[quantizer]
                    ), f"Quantizer {quantizer} does not have the enabled field: {schema}"
                    schema[quantizer]["enabled"] = False
            elif isinstance(val, _ConfigUpdateModel):
                schema[cls_field] = val.merge_with_existing(schema[cls_field])
            else:
                pass  # ignore unknown types so that individual classes can be extended
        return schema


@dataclass
class _ConfigBase:
    def to_dict(self) -> dict:
        out = {}
        for k, v in self.__dict__.items():
            words = k.split("_")
            key = words[0].lower() + "".join(word.title() for word in words[1:])
            if v is None:
                continue
            if isinstance(v, Enum):
                out[key] = v.value
                continue
            if isinstance(v, dict):
                out[key] = {
                    k: v.to_dict() if isinstance(v, _ConfigBase) else v for k, v in v.items()
                }
                continue
            out[key] = v.to_dict() if isinstance(v, _ConfigBase) else v
        return out


class _QuantizerConfigCreate(_ConfigCreateModel):
    enabled: bool = Field(default=True)

    @staticmethod
    @abstractmethod
    def quantizer_name() -> str:
        ...


class _QuantizerConfigUpdate(_ConfigUpdateModel):
    @staticmethod
    @abstractmethod
    def quantizer_name() -> str:
        ...


@dataclass
class _EnumLikeStr:
    string: str

    @property
    def value(self) -> str:
        return self.string
