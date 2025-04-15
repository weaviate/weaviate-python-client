"""Backup class definition."""

import asyncio
import time
from typing import Generic, Optional, Union, List, Tuple, Dict

from httpx import Response

from weaviate.backup.backup import (
    BackupStorage,
    BackupReturn,
    BackupStatusReturn,
    STORAGE_NAMES,
    BackupConfigCreate,
    BackupStatus,
    BackupConfigRestore,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, Connection, ConnectionAsync, ConnectionType
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


class _BackupExecutor(Generic[ConnectionType]):
    def __init__(self, connection: Connection):
        self._connection = connection

    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> executor.Result[BackupReturn]:
        """Create a backup of all/per collection Weaviate objects.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage where to create the backup.
            include_collections: The collection/list of collections to be included in the backup. If not specified all
                collections will be included. Either `include_collections` or `exclude_collections` can be set. By default None.
            exclude_collections: The collection/list of collections to be excluded in the backup.
                Either `include_collections` or `exclude_collections` can be set. By default None.
            wait_for_completion: Whether to wait until the backup is done. By default False.
            config: The configuration of the backup creation. By default None.
            backup_location: The dynamic location of a backup. By default None.

        Returns:
             A `_BackupReturn` object that contains the backup creation response.

        Raises:
            requests.ConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
            TypeError: One of the arguments have a wrong type.
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
            payload["config"] = config._to_dict()

        if backup_location is not None:
            if self._connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCreate dynamic backup location",
                    str(self._connection._weaviate_version),
                    "1.27.2",
                )
            if "config" not in payload:
                payload["config"] = {}
            payload["config"].update(backup_location._to_dict())

        path = f"/backups/{backend.value}"

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> BackupReturn:
                res = await executor.aresult(
                    self._connection.post(
                        path=path,
                        weaviate_object=payload,
                        error_msg="Backup creation failed due to connection error.",
                    )
                )
                create_status = _decode_json_response_dict(res, "Backup creation")
                assert create_status is not None
                if wait_for_completion:
                    while True:
                        status = await executor.aresult(
                            self.get_create_status(
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

        res = executor.result(
            self._connection.post(
                path=path,
                weaviate_object=payload,
                error_msg="Backup creation failed due to connection error.",
            )
        )
        create_status = _decode_json_response_dict(res, "Backup creation")
        assert create_status is not None
        if wait_for_completion:
            while True:
                status = executor.result(
                    self.get_create_status(
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
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> executor.Result[BackupStatusReturn]:
        """Checks if a started backup job has completed.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage where the backup was created.
            backup_location: The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup creation status response.
        """
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,  # this check can be removed when we remove the old backup class
        )

        path = f"/backups/{backend.value}/{backup_id}"
        params: Dict[str, str] = {}
        if backup_location is not None:
            if self._connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCreateStatus dynamic backup location",
                    str(self._connection._weaviate_version),
                    "1.27.2",
                )

            params.update(backup_location._to_dict())

        def resp(res: Response) -> BackupStatusReturn:
            typed_response = _decode_json_response_dict(res, "Backup status check")
            if typed_response is None:
                raise EmptyResponseException()
            typed_response["id"] = backup_id
            return BackupStatusReturn(**typed_response)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            params=params,
            error_msg="Backup creation status failed due to connection error.",
        )

    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> executor.Result[BackupReturn]:
        """Restore a backup of all/per collection Weaviate objects.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage from where to restore the backup.
            include_collections: The collection/list of collections to be included in the backup restore. If not specified all
                collections will be included (that were backup-ed). Either `include_collections` or
                `exclude_collections` can be set. By default None.
            exclude_collections: The collection/list of collections to be excluded in the backup restore.
                Either `include_collections` or `exclude_collections` can be set. By default None.
            wait_for_completion: Whether to wait until the backup restore is done.
            config: The configuration of the backup restoration. By default None.
            backup_location: The dynamic location of a backup. By default None.

        Returns:
            A `BackupReturn` object that contains the backup restore response.

        Raises:
            requests.ConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
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
            payload["config"] = config._to_dict()

        if backup_location is not None:
            if self._connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigRestore dynamic backup location",
                    str(self._connection._weaviate_version),
                    "1.27.2",
                )

            if "config" not in payload:
                payload["config"] = {}
            payload["config"].update(backup_location._to_dict())

        path = f"/backups/{backend.value}/{backup_id}/restore"

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> BackupReturn:
                response = await executor.aresult(
                    self._connection.post(
                        path=path,
                        weaviate_object=payload,
                        error_msg="Backup restore failed due to connection error.",
                    )
                )
                restore_status = _decode_json_response_dict(response, "Backup restore")
                assert restore_status is not None
                if wait_for_completion:
                    while True:
                        status = await executor.aresult(
                            self.get_restore_status(
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

        response = executor.result(
            self._connection.post(
                path=path,
                weaviate_object=payload,
                error_msg="Backup restore failed due to connection error.",
            )
        )
        restore_status = _decode_json_response_dict(response, "Backup restore")
        assert restore_status is not None
        if wait_for_completion:
            while True:
                status = executor.result(
                    self.get_restore_status(
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
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> executor.Result[BackupStatusReturn]:
        """Checks if a started restore job has completed.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage where to create the backup.
            backup_location: The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup restore status response.
        """
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}/restore"

        params: Dict[str, str] = {}
        if backup_location is not None:
            if self._connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigRestore status dynamic backup location",
                    str(self._connection._weaviate_version),
                    "1.27.2",
                )
            params.update(backup_location._to_dict())

        def resp(res: Response) -> BackupStatusReturn:
            typed_response = _decode_json_response_dict(res, "Backup restore status check")
            if typed_response is None:
                raise EmptyResponseException()
            typed_response["id"] = backup_id
            return BackupStatusReturn(**typed_response)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            params=params,
            error_msg="Backup restore status failed due to connection error.",
        )

    def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> executor.Result[bool]:
        """Cancels a running backup.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage where to create the backup.
            backup_location: The dynamic location of a backup. By default None.

        Raises:
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.

        Returns:
            A bool indicating if the cancellation was successful.
        """
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}"
        params: Dict[str, str] = {}

        if backup_location is not None:
            if self._connection._weaviate_version.is_lower_than(1, 27, 2):
                raise WeaviateUnsupportedFeatureError(
                    "BackupConfigCancel dynamic backup location",
                    str(self._connection._weaviate_version),
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

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
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
    """Validate and return the Backup.create/Backup.restore arguments.

    Args:
        backup_id: The identifier name of the backup.
        backend: The backend storage. Currently available options are: "filesystem", "s3", "gcs" and "azure".
        include_classes: The class/list of classes to be included in the backup. If not specified all classes
            will be included. Either `include_classes` or `exclude_classes` can be set.
        exclude_classes: The class/list of classes to be excluded from the backup.
            Either `include_classes` or `exclude_classes` can be set.
        wait_for_completion: Whether to wait until the backup restore is done.

    Returns:
        Validated and processed (backup_id, backend, include_classes, exclude_classes).

    Raises:
        TypeError: If one of the arguments have a wrong type.
        ValueError: If 'backend' does not have an accepted value.
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
    """Checks if a started classification job has completed.

    Args:
        backup_id: The identifier name of the backup. NOTE: Case insensitive.
        backend: The backend storage where to create the backup. Currently available options are:
                "filesystem", "s3", "gcs" and "azure".

    Returns:
        Validated and processed (backup_id, backend, include_classes, exclude_classes).

    Raises:
        TypeError: One of the arguments is of a wrong type.
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
