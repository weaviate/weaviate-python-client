from typing import Dict, Any, cast, Union

from pydantic import BaseModel


class _DynamicPathConfig(BaseModel):
    """The dynamic path of a backup."""

    def _to_dict(self) -> Dict[str, Any]:
        ret = cast(dict, self.model_dump(exclude_none=True))

        return ret


class _DynamicPathFilesystem(_DynamicPathConfig):
    """The dynamic path of a backup for filesystem."""

    path: str


class _DynamicPathS3(_DynamicPathConfig):
    """The dynamic path of a backup for S3."""

    path: str
    bucket: str


class _DynamicPathGCP(_DynamicPathConfig):
    """The dynamic path of a backup for GCP."""

    path: str
    bucket: str


class _DynamicPathAzure(_DynamicPathConfig):
    """The dynamic path of a backup for Azure."""

    path: str
    bucket: str


DynamicPathType = Union[_DynamicPathFilesystem, _DynamicPathS3, _DynamicPathGCP, _DynamicPathAzure]


class DynamicPath:
    """The dynamic path of a backup."""

    FileSystem = _DynamicPathFilesystem
    S3 = _DynamicPathS3
    GCP = _DynamicPathGCP
    Azure = _DynamicPathAzure
