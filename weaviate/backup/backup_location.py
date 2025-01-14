from typing import Dict, Any, cast, Union

from pydantic import BaseModel


class _BackupLocationConfig(BaseModel):
    """The dynamic location of a backup."""

    def _to_dict(self) -> Dict[str, Any]:
        ret = cast(dict, self.model_dump(exclude_none=True))

        return ret


class _BackupLocationFilesystem(_BackupLocationConfig):
    """The dynamic location of a backup for filesystem."""

    path: str


class _BackupLocationS3(_BackupLocationConfig):
    """The dynamic location of a backup for S3."""

    path: str
    bucket: str


class _BackupLocationGCP(_BackupLocationConfig):
    """The dynamic location of a backup for GCP."""

    path: str
    bucket: str


class _BackupLocationAzure(_BackupLocationConfig):
    """The dynamic location of a backup for Azure."""

    path: str
    bucket: str


BackupLocationType = Union[
    _BackupLocationFilesystem, _BackupLocationS3, _BackupLocationGCP, _BackupLocationAzure
]


class BackupLocation:
    """The dynamic path of a backup."""

    FileSystem = _BackupLocationFilesystem
    S3 = _BackupLocationS3
    GCP = _BackupLocationGCP
    Azure = _BackupLocationAzure
