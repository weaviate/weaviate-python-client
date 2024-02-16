from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, cast
from pydantic import BaseModel, ConfigDict


class _ConfigCreateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def _to_dict(self) -> Dict[str, Any]:
        return cast(dict, self.model_dump(exclude_none=True))


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
