"""
Backup class definition.
"""

from enum import Enum
from time import sleep
from typing import Optional, Union, List, Tuple

from pydantic import BaseModel, Field

from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
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
    _decode_json_response_list,
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


class _BackupAsync:
    """Backup class used to schedule and/or check the status of a backup process of Weaviate objects."""

    def __init__(self, connection: ConnectionV4):
        self._connection = connection

    async def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Optional[Union[List[str], str]] = None,
        exclude_collections: Optional[Union[List[str], str]] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
    ) -> BackupReturn:
        """Create a backup of all/per collection Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage where to create the backup.
        include_collections : Union[List[str], str], optional
            The collection/list of collections to be included in the backup. If not specified all
            collections will be included. Either `include_collections` or `exclude_collections` can be set. By default None.
        exclude_collections : Union[List[str], str], optional
            The collection/list of collections to be excluded in the backup.
            Either `include_collections` or `exclude_collections` can be set. By default None.
        wait_for_completion : bool, optional
            Whether to wait until the backup is done. By default False.
        config: BackupConfigCreate, optional
            The configuration of the backup creation. By default None.

        Returns
        -------
         A `_BackupReturn` object that contains the backup creation response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            One of the arguments have a wrong type.
        """
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
            if self._connection._weaviate_version.is_lower_than(1, 25, 0):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCreate", str(self._connection._weaviate_version), "1.25.0"
                )
            if not isinstance(config, BackupConfigCreate):
                raise WeaviateInvalidInputError(
                    f"Expected 'config' to be of type 'BackupConfigCreate', but got {type(config)}."
                )
            payload["config"] = config.model_dump()

        path = f"/backups/{backend.value}"

        response = await self._connection.post(
            path=path,
            weaviate_object=payload,
            error_msg="Backup creation failed due to connection error.",
        )

        create_status = _decode_json_response_dict(response, "Backup creation")
        assert create_status is not None
        if wait_for_completion:
            while True:
                status = await self.__get_create_status(
                    backup_id=backup_id,
                    backend=backend,
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
                sleep(1)
        return BackupReturn(**create_status)

    async def __get_create_status(
        self, backup_id: str, backend: BackupStorage
    ) -> BackupStatusReturn:
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,  # this check can be removed when we remove the old backup class
        )

        path = f"/backups/{backend.value}/{backup_id}"

        response = await self._connection.get(
            path=path, error_msg="Backup creation status failed due to connection error."
        )

        typed_response = _decode_json_response_dict(response, "Backup status check")
        if typed_response is None:
            raise EmptyResponseException()
        typed_response["id"] = backup_id
        return BackupStatusReturn(**typed_response)

    async def get_create_status(self, backup_id: str, backend: BackupStorage) -> BackupStatusReturn:
        """
        Checks if a started backup job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage eNUM
            The backend storage where the backup was created.

        Returns
        -------
         A `BackupStatusReturn` object that contains the backup creation status response.
        """
        return await self.__get_create_status(backup_id, backend)

    async def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
    ) -> BackupReturn:
        """
        Restore a backup of all/per collection Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage from where to restore the backup.
        include_collections : Union[List[str], str], optional
            The collection/list of collections to be included in the backup restore. If not specified all
            collections will be included (that were backup-ed). Either `include_collections` or
            `exclude_collections` can be set. By default None.
        exclude_collections : Union[List[str], str], optional
            The collection/list of collections to be excluded in the backup restore.
            Either `include_collections` or `exclude_collections` can be set. By default None.
        wait_for_completion : bool, optional
            Whether to wait until the backup restore is done.
        config: BackupConfigRestore, optional
            The configuration of the backup restoration. By default None.

        Returns
        -------
         A `BackupReturn` object that contains the backup restore response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """
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
            if self._connection._weaviate_version.is_lower_than(1, 25, 0):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigRestore", str(self._connection._weaviate_version), "1.25.0"
                )
            if not isinstance(config, BackupConfigRestore):
                raise WeaviateInvalidInputError(
                    f"Expected 'config' to be of type 'BackupConfigRestore', but got {type(config)}."
                )
            payload["config"] = config.model_dump()

        path = f"/backups/{backend.value}/{backup_id}/restore"
        response = await self._connection.post(
            path=path,
            weaviate_object=payload,
            error_msg="Backup restore failed due to connection error.",
        )
        restore_status = _decode_json_response_dict(response, "Backup restore")
        assert restore_status is not None
        if wait_for_completion:
            while True:
                status = await self.__get_restore_status(
                    backup_id=backup_id,
                    backend=backend,
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

                sleep(1)
        return BackupReturn(**restore_status)

    async def __get_restore_status(
        self, backup_id: str, backend: BackupStorage
    ) -> BackupStatusReturn:
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}/restore"

        response = await self._connection.get(
            path=path, error_msg="Backup restore status failed due to connection error."
        )
        typed_response = _decode_json_response_dict(response, "Backup restore status check")
        if typed_response is None:
            raise EmptyResponseException()
        typed_response["id"] = backup_id
        return BackupStatusReturn(**typed_response)

    async def get_restore_status(
        self, backup_id: str, backend: BackupStorage
    ) -> BackupStatusReturn:
        """
        Checks if a started restore job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage where to create the backup.

        Returns
        -------
         A `BackupStatusReturn` object that contains the backup restore status response.
        """
        return await self.__get_restore_status(backup_id, backend)

    async def __cancel_backup(self, backup_id: str, backend: BackupStorage) -> bool:
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}"

        response = await self._connection.delete(
            path=path,
            error_msg="Backup cancel failed due to connection error.",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="delete object"),
        )

        if response.status_code == 204:
            return True  # Successfully deleted
        else:
            typed_response = _decode_json_response_dict(response, "Backup cancel")
            if typed_response is None:
                raise EmptyResponseException()
            return False  # did not exist

    async def cancel(self, backup_id: str, backend: BackupStorage) -> bool:
        """
        Cancels a running backup.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage where to create the backup.

        Raises
        ------
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.

        Returns
        -------
         A bool indicating if the cancellation was successful.
        """
        return await self.__cancel_backup(backup_id, backend)

    async def __list_backups(self, backend: BackupStorage) -> List[BackupReturn]:
        _, backend = _get_and_validate_get_status(backend=backend, backup_id="dummy")
        path = f"/backups/{backend.value}"

        response = await self._connection.get(
            path=path, error_msg="Backup list status failed due to connection error."
        )
        typed_response = _decode_json_response_list(response, "Backup list")
        if typed_response is None:
            raise EmptyResponseException()
        return [BackupReturn(**entry) for entry in typed_response]

    # did not make it into 1.27, will come later
    # async def list_backups(self, backend: BackupStorage) -> List[BackupReturn]:
    #     """
    #     List all backups that are currently in progress.
    #
    #     Parameters
    #     ----------
    #     backend : BackupStorage
    #         The backend storage where to create the backup.
    #
    #     Returns
    #     -------
    #      A list of `BackupStatusReturn` objects that contain the backup restore status responses.
    #     """
    #     return await self.__list_backups(backend)


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
