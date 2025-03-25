"""
Backup class definition.
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Union, List, Tuple, Dict, Any, cast

from httpx import Response
from pydantic import BaseModel, Field

from weaviate.backup.backup_location import _BackupLocationConfig, BackupLocationType
from weaviate.connect.executor import execute, ExecutorResult, aresult, result
from weaviate.connect.v4 import _ExpectedStatusCodes, Connection, ConnectionAsync
from weaviate.exceptions import (
    WeaviateInvalidInputError,
    WeaviateUnsupportedFeatureError,
    BackupFailedException,
    EmptyResponseException,
    BackupCanceledError,
)
from weaviate.util import (
    _capitalize_first_letter,
    _decode_json_response_dict,
)

STORAGE_NAMES = {
    "filesystem",
    "s3",
    "gcs",
    "azure",
}


class BackupCompressionLevel(str, Enum):
    """Which compression level should be used to compress the backup."""

    DEFAULT = "DefaultCompression"
    BEST_SPEED = "BestSpeed"
    BEST_COMPRESSION = "BestCompression"


class BackupStorage(str, Enum):
    """Which backend should be used to write the backup to."""

    FILESYSTEM = "filesystem"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


class BackupStatus(str, Enum):
    """The status of a backup."""

    STARTED = "STARTED"
    TRANSFERRING = "TRANSFERRING"
    TRANSFERRED = "TRANSFERRED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class _BackupConfigBase(BaseModel):
    CPUPercentage: Optional[int] = Field(default=None, alias="cpu_percentage")

    def _to_dict(self) -> Dict[str, Any]:
        ret = cast(dict, self.model_dump(exclude_none=True))

        for key, val in ret.items():
            if isinstance(val, _BackupLocationConfig):
                ret[key] = val._to_dict()

        return ret


class BackupConfigCreate(_BackupConfigBase):
    """Options to configure the backup when creating a backup."""

    ChunkSize: Optional[int] = Field(default=None, alias="chunk_size")
    CompressionLevel: Optional[BackupCompressionLevel] = Field(
        default=None, alias="compression_level"
    )


class BackupConfigRestore(_BackupConfigBase):
    """Options to configure the backup when restoring a backup."""


class BackupStatusReturn(BaseModel):
    """Return type of the backup status methods."""

    error: Optional[str] = Field(default=None)
    status: BackupStatus
    path: str
    backup_id: str = Field(alias="id")


class BackupReturn(BackupStatusReturn):
    """Return type of the backup creation and restore methods."""

    collections: List[str] = Field(default_factory=list, alias="classes")


class _BackupExecutor:
    def create(
        self,
        connection: Connection,
        *,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupReturn]:
        (
            backup_id,
            backend,
            include_collections,
            exclude_collections,
        ) = _get_and_validate_create_restore_arguments(
            backup_id=backup_id,
            backend=backend,  # can be removed when we remove the old backup class
            include_classes=include_collections,
            exclude_classes=exclude_collections,
            wait_for_completion=wait_for_completion,
        )

        payload: dict = {
            "id": backup_id,
            "include": include_collections,
            "exclude": exclude_collections,
        }

        if config is not None:
            if connection._weaviate_version.is_lower_than(1, 25, 0):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCreate", str(connection._weaviate_version), "1.25.0"
                )
            if not isinstance(config, BackupConfigCreate):
                raise WeaviateInvalidInputError(
                    f"Expected 'config' to be of type 'BackupConfigCreate', but got {type(config)}."
                )
            payload["config"] = config._to_dict()

        if backup_location is not None:
            if connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCreate dynamic backup location",
                    str(connection._weaviate_version),
                    "1.27.2",
                )
            if "config" not in payload:
                payload["config"] = {}
            payload["config"].update(backup_location._to_dict())

        path = f"/backups/{backend.value}"

        if isinstance(connection, ConnectionAsync):

            async def _execute() -> BackupReturn:
                res = await aresult(
                    connection.post(
                        path=path,
                        weaviate_object=payload,
                        error_msg="Backup creation failed due to connection error.",
                    )
                )
                create_status = _decode_json_response_dict(res, "Backup creation")
                assert create_status is not None
                if wait_for_completion:
                    while True:
                        status = await aresult(
                            self.get_create_status(
                                connection=connection,
                                backup_id=backup_id,
                                backend=backend,
                                backup_location=backup_location,
                            )
                        )
                        create_status["status"] = status.status
                        if status.status == BackupStatus.SUCCESS:
                            break
                        if status.status == BackupStatus.FAILED:
                            raise BackupFailedException(
                                f"Backup failed: {create_status} with error: {status.error}"
                            )
                        if status.status == BackupStatus.CANCELED:
                            raise BackupCanceledError(
                                f"Backup was canceled: {create_status} with error: {status.error}"
                            )
                        await asyncio.sleep(1)
                return BackupReturn(**create_status)

            return _execute()

        res = result(
            connection.post(
                path=path,
                weaviate_object=payload,
                error_msg="Backup creation failed due to connection error.",
            )
        )
        create_status = _decode_json_response_dict(res, "Backup creation")
        assert create_status is not None
        if wait_for_completion:
            while True:
                status = result(
                    self.get_create_status(
                        connection=connection,
                        backup_id=backup_id,
                        backend=backend,
                        backup_location=backup_location,
                    )
                )
                create_status["status"] = status.status
                if status.status == BackupStatus.SUCCESS:
                    break
                if status.status == BackupStatus.FAILED:
                    raise BackupFailedException(
                        f"Backup failed: {create_status} with error: {status.error}"
                    )
                if status.status == BackupStatus.CANCELED:
                    raise BackupCanceledError(
                        f"Backup was canceled: {create_status} with error: {status.error}"
                    )
                time.sleep(1)
        return BackupReturn(**create_status)

    def get_create_status(
        self,
        connection: Connection,
        *,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType],
    ) -> ExecutorResult[BackupStatusReturn]:
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,  # this check can be removed when we remove the old backup class
        )

        path = f"/backups/{backend.value}/{backup_id}"
        params: Dict[str, str] = {}
        if backup_location is not None:
            if connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCreateStatus dynamic backup location",
                    str(connection._weaviate_version),
                    "1.27.2",
                )

            params.update(backup_location._to_dict())

        def resp(res: Response) -> BackupStatusReturn:
            typed_response = _decode_json_response_dict(res, "Backup status check")
            if typed_response is None:
                raise EmptyResponseException()
            typed_response["id"] = backup_id
            return BackupStatusReturn(**typed_response)

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            params=params,
            error_msg="Backup creation status failed due to connection error.",
        )

    def restore(
        self,
        connection: Connection,
        *,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool,
        config: Optional[BackupConfigRestore],
        backup_location: Optional[BackupLocationType],
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
    ) -> ExecutorResult[BackupReturn]:
        (
            backup_id,
            backend,
            include_collections,
            exclude_collections,
        ) = _get_and_validate_create_restore_arguments(
            backup_id=backup_id,
            backend=backend,
            include_classes=include_collections,
            exclude_classes=exclude_collections,
            wait_for_completion=wait_for_completion,
        )

        payload: dict = {
            "include": include_collections,
            "exclude": exclude_collections,
        }

        if config is not None:
            if connection._weaviate_version.is_lower_than(1, 25, 0):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigRestore", str(connection._weaviate_version), "1.25.0"
                )
            if not isinstance(config, BackupConfigRestore):
                raise WeaviateInvalidInputError(
                    f"Expected 'config' to be of type 'BackupConfigRestore', but got {type(config)}."
                )
            payload["config"] = config._to_dict()

        if backup_location is not None:
            if connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigRestore dynamic backup location",
                    str(connection._weaviate_version),
                    "1.27.2",
                )

            if "config" not in payload:
                payload["config"] = {}
            payload["config"].update(backup_location._to_dict())

        path = f"/backups/{backend.value}/{backup_id}/restore"

        if isinstance(connection, ConnectionAsync):

            async def _execute() -> BackupReturn:
                response = await aresult(
                    connection.post(
                        path=path,
                        weaviate_object=payload,
                        error_msg="Backup restore failed due to connection error.",
                    )
                )
                restore_status = _decode_json_response_dict(response, "Backup restore")
                assert restore_status is not None
                if wait_for_completion:
                    while True:
                        status = await aresult(
                            self.get_restore_status(
                                connection=connection,
                                backup_id=backup_id,
                                backend=backend,
                                backup_location=backup_location,
                            )
                        )
                        restore_status["status"] = status.status
                        if status.status == BackupStatus.SUCCESS:
                            break
                        if status.status == BackupStatus.FAILED:
                            raise BackupFailedException(
                                f"Backup restore failed: {restore_status} with error: {status.error}"
                            )
                        if status.status == BackupStatus.CANCELED:
                            raise BackupCanceledError(
                                f"Backup restore canceled: {restore_status} with error: {status.error}"
                            )

                        await asyncio.sleep(1)
                return BackupReturn(**restore_status)

            return _execute()

        response = result(
            connection.post(
                path=path,
                weaviate_object=payload,
                error_msg="Backup restore failed due to connection error.",
            )
        )
        restore_status = _decode_json_response_dict(response, "Backup restore")
        assert restore_status is not None
        if wait_for_completion:
            while True:
                status = result(
                    self.get_restore_status(
                        connection=connection,
                        backup_id=backup_id,
                        backend=backend,
                        backup_location=backup_location,
                    )
                )
                restore_status["status"] = status.status
                if status.status == BackupStatus.SUCCESS:
                    break
                if status.status == BackupStatus.FAILED:
                    raise BackupFailedException(
                        f"Backup restore failed: {restore_status} with error: {status.error}"
                    )
                if status.status == BackupStatus.CANCELED:
                    raise BackupCanceledError(
                        f"Backup restore canceled: {restore_status} with error: {status.error}"
                    )

                time.sleep(1)
        return BackupReturn(**restore_status)

    def get_restore_status(
        self,
        connection: Connection,
        *,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType],
    ) -> ExecutorResult[BackupStatusReturn]:
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}/restore"

        params: Dict[str, str] = {}
        if backup_location is not None:
            if connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigRestore status dynamic backup location",
                    str(connection._weaviate_version),
                    "1.27.2",
                )
            params.update(backup_location._to_dict())

        def resp(res: Response) -> BackupStatusReturn:
            typed_response = _decode_json_response_dict(res, "Backup restore status check")
            if typed_response is None:
                raise EmptyResponseException()
            typed_response["id"] = backup_id
            return BackupStatusReturn(**typed_response)

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            params=params,
            error_msg="Backup restore status failed due to connection error.",
        )

    def cancel(
        self,
        connection: Connection,
        *,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType],
    ) -> ExecutorResult[bool]:
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}"
        params: Dict[str, str] = {}

        if backup_location is not None:
            if connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCancel dynamic backup location",
                    str(connection._weaviate_version),
                    "1.27.2",
                )
            params.update(backup_location._to_dict())

        def resp(res: Response) -> bool:
            if res.status_code == 204:
                return True
            typed_response = _decode_json_response_dict(res, "Backup cancel")
            if typed_response is None:
                raise EmptyResponseException()
            return False

        return execute(
            response_callback=resp,
            method=connection.delete,
            path=path,
            params=params,
            error_msg="Backup cancel failed due to connection error.",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="delete object"),
        )

    # did not make it into 1.27, will come later
    # async def list_backups(self, backend: BackupStorage) -> List[BackupReturn]:
    #     _, backend = _get_and_validate_get_status(backend=backend, backup_id="dummy")
    #     path = f"/backups/{backend.value}"

    #     response = await self._connection.get(
    #         path=path, error_msg="Backup list status failed due to connection error."
    #     )
    #     typed_response = _decode_json_response_list(response, "Backup list")
    #     if typed_response is None:
    #         raise EmptyResponseException()
    #     return [BackupReturn(**entry) for entry in typed_response]


def _get_and_validate_create_restore_arguments(
    backup_id: str,
    backend: Union[str, BackupStorage],
    include_classes: Union[List[str], str, None],
    exclude_classes: Union[List[str], str, None],
    wait_for_completion: bool,
) -> Tuple[str, BackupStorage, List[str], List[str]]:
    """
    Validate and return the Backup.create/Backup.restore arguments.

    Parameters
    ----------
    backup_id : str
        The identifier name of the backup.
    backend : str
        The backend storage. Currently available options are:
            "filesystem", "s3", "gcs" and "azure".
    include_classes : Union[List[str], str, None]
        The class/list of classes to be included in the backup. If not specified all classes
        will be included. Either `include_classes` or `exclude_classes` can be set.
    exclude_classes : Union[List[str], str, None]
        The class/list of classes to be excluded from the backup.
        Either `include_classes` or `exclude_classes` can be set.
    wait_for_completion : bool
        Whether to wait until the backup restore is done.

    Returns
    -------
    Tuple[str, str, List[str], List[str]]
        Validated and processed (backup_id, backend, include_classes, exclude_classes).

    Raises
    ------
    TypeError
        One of the arguments have a wrong type.
    ValueError
        'backend' does not have an accepted value.
    """

    if not isinstance(backup_id, str):
        raise TypeError(f"'backup_id' must be of type str. Given type: {type(backup_id)}.")
    if isinstance(backend, str):
        try:
            backend = BackupStorage(backend.lower())
        except KeyError:
            raise ValueError(
                f"'backend' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {backend}."
            )

    if not isinstance(wait_for_completion, bool):
        raise TypeError(
            f"'wait_for_completion' must be of type bool. Given type: {type(wait_for_completion)}."
        )

    if include_classes is not None:
        if isinstance(include_classes, str):
            include_classes = [include_classes]
        elif not isinstance(include_classes, list):
            raise TypeError(
                "'include_classes' must be of type str, list of str or None. "
                f"Given type: {type(include_classes)}."
            )
    else:
        include_classes = []

    if exclude_classes is not None:
        if isinstance(exclude_classes, str):
            exclude_classes = [exclude_classes]
        elif not isinstance(exclude_classes, list):
            raise TypeError(
                "'exclude_classes' must be of type str, list of str or None. "
                f"Given type: {type(exclude_classes)}."
            )
    else:
        exclude_classes = []

    if include_classes and exclude_classes:
        raise TypeError("Either 'include_classes' OR 'exclude_classes' can be set, not both.")

    include_classes = [_capitalize_first_letter(cls) for cls in include_classes]
    exclude_classes = [_capitalize_first_letter(cls) for cls in exclude_classes]

    return (backup_id.lower(), backend, include_classes, exclude_classes)


def _get_and_validate_get_status(
    backup_id: str, backend: Union[str, BackupStorage]
) -> Tuple[str, BackupStorage]:
    """
    Checks if a started classification job has completed.

    Parameters
    ----------
    backup_id : str
        The identifier name of the backup.
        NOTE: Case insensitive.
    backend : str
        The backend storage where to create the backup. Currently available options are:
            "filesystem", "s3", "gcs" and "azure".

    Returns
    -------
    Tuple[str, str]
        Validated and processed (backup_id, backend, include_classes, exclude_classes).

    Raises
    ------
    TypeError
        One of the arguments is of a wrong type.
    """

    if not isinstance(backup_id, str):
        raise TypeError(f"'backup_id' must be of type str. Given type: {type(backup_id)}.")
    if isinstance(backend, str):
        try:
            backend = BackupStorage(backend.lower())
        except KeyError:
            raise ValueError(
                f"'backend' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {backend}."
            )

    return (backup_id.lower(), backend)
