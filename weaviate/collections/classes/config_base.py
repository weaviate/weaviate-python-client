from typing import Any, Dict, cast
from pydantic import BaseModel, ConfigDict


class _ConfigCreateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def _to_dict(self) -> Dict[str, Any]:
        return cast(dict, self.model_dump(exclude_none=True))
