"""
Backup class definition.
"""

from enum import Enum
from time import sleep
from typing import Optional, Union, List, Tuple, Any, Dict
from pydantic import BaseModel, Field

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection, ConnectionV4
from weaviate.exceptions import (
    BackupFailedException,
    EmptyResponseException,
)
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict

STORAGE_NAMES = {
    "filesystem",
    "s3",
    "gcs",
    "azure",
}


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


class BackupStatusReturn(BaseModel):
    """Return type of the backup status methods."""

    status: BackupStatus
    path: str


class BackupReturn(BackupStatusReturn):
    """Return type of the backup creation and restore methods."""

    collections: List[str] = Field(default_factory=list, alias="classes")


class _Backup:
    """Backup class used to schedule and/or check the status of a backup process of Weaviate objects."""

    def __init__(self, connection: ConnectionV4):
        self._connection = connection

    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Optional[Union[List[str], str]] = None,
        exclude_collections: Optional[Union[List[str], str]] = None,
        wait_for_completion: bool = False,
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

        payload = {
            "id": backup_id,
            "include": include_collections,
            "exclude": exclude_collections,
        }
        path = f"/backups/{backend.value}"

        response = self._connection.post(
            path=path,
            weaviate_object=payload,
            error_msg="Backup creation failed due to connection error.",
        )

        create_status = _decode_json_response_dict(response, "Backup creation")
        assert create_status is not None
        if wait_for_completion:
            while True:
                status = self.get_create_status(
                    backup_id=backup_id,
                    backend=backend,
                )
                create_status["status"] = status.status
                if status.status == BackupStatus.SUCCESS:
                    break
                if status.status == BackupStatus.FAILED:
                    raise BackupFailedException(f"Backup failed: {create_status}")
                sleep(1)
        return BackupReturn(**create_status)

    def get_create_status(self, backup_id: str, backend: BackupStorage) -> BackupStatusReturn:
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
        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,  # this check can be removed when we remove the old backup class
        )

        path = f"/backups/{backend.value}/{backup_id}"

        response = self._connection.get(
            path=path, error_msg="Backup creation status failed due to connection error."
        )

        typed_response = _decode_json_response_dict(response, "Backup status check")
        if typed_response is None:
            raise EmptyResponseException()
        return BackupStatusReturn(**typed_response)

    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
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

        payload = {
            "include": include_collections,
            "exclude": exclude_collections,
        }
        path = f"/backups/{backend.value}/{backup_id}/restore"
        response = self._connection.post(
            path=path,
            weaviate_object=payload,
            error_msg="Backup restore failed due to connection error.",
        )
        restore_status = _decode_json_response_dict(response, "Backup restore")
        assert restore_status is not None
        if wait_for_completion:
            while True:
                status = self.get_restore_status(
                    backup_id=backup_id,
                    backend=backend,
                )
                restore_status["status"] = status.status
                if status.status == BackupStatus.SUCCESS:
                    break
                if status.status == BackupStatus.FAILED:
                    raise BackupFailedException(f"Backup restore failed: {restore_status}")
                sleep(1)
        return BackupReturn(**restore_status)

    def get_restore_status(self, backup_id: str, backend: BackupStorage) -> BackupStatusReturn:
        """
        Checks if a started classification job has completed.

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

        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}/restore"

        response = self._connection.get(
            path=path, error_msg="Backup restore status failed due to connection error."
        )
        typed_response = _decode_json_response_dict(response, "Backup restore status check")
        if typed_response is None:
            raise EmptyResponseException()
        return BackupStatusReturn(**typed_response)


class Backup:
    """
    Backup class used to schedule and/or check the status of
    a backup process of Weaviate objects.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Classification class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        """

        self._connection = connection

    def create(
        self,
        backup_id: str,
        backend: str,
        include_classes: Union[List[str], str, None] = None,
        exclude_classes: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
    ) -> dict:
        """
        Create a backup of all/per class Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : str
            The backend storage where to create the backup. Currently available options are:
                "filesystem", "s3", "gcs" and "azure".
            NOTE: Case insensitive.
        include_classes : Union[List[str], str, None], optional
            The class/list of classes to be included in the backup. If not specified all classes
            will be included. Either `include_classes` or `exclude_classes` can be set.
            By default None.
        exclude_classes : Union[List[str], str, None], optional
            The class/list of classes to be excluded in the backup. Either `include_classes` or
            `exclude_classes` can be set. By default None.
        wait_for_completion : bool, optional
            Whether to wait until the backup is done. By default False.

        Returns
        -------
        dict
            Backup creation response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            One of the arguments have a wrong type.
        ValueError
            'backend' does not have an accepted value.
        """

        (
            backup_id,
            backend,
            include_classes,
            exclude_classes,
        ) = _get_and_validate_create_restore_arguments(
            backup_id=backup_id,
            backend=backend,
            include_classes=include_classes,
            exclude_classes=exclude_classes,
            wait_for_completion=wait_for_completion,
        )

        payload = {
            "id": backup_id,
            "include": include_classes,
            "exclude": exclude_classes,
        }
        path = f"/backups/{backend.value}"

        try:
            response = self._connection.post(
                path=path,
                weaviate_object=payload,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Backup creation failed due to connection error."
            ) from conn_err

        create_status = _decode_json_response_dict(response, "Backup creation")
        assert create_status is not None
        if wait_for_completion:
            while True:
                status: dict = self.get_create_status(
                    backup_id=backup_id,
                    backend=backend,
                )
                create_status.update(status)
                if status["status"] == "SUCCESS":
                    break
                if status["status"] == "FAILED":
                    raise BackupFailedException(f"Backup failed: {create_status}")
                sleep(1)
        return create_status

    def get_create_status(self, backup_id: str, backend: str) -> Dict[str, Any]:
        """
        Checks if a started classification job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : str
            The backend storage where the backup was created. Currently available options are:
                "filesystem", "s3", "gcs" and "azure".
            NOTE: Case insensitive.

        Returns
        -------
        dict
            Status of the backup create.
        """

        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )

        path = f"/backups/{backend.value}/{backup_id}"

        try:
            response = self._connection.get(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Backup creation status failed due to connection error."
            ) from conn_err

        typed_response = _decode_json_response_dict(response, "Backup status check")
        if typed_response is None:
            raise EmptyResponseException()
        return typed_response

    def restore(
        self,
        backup_id: str,
        backend: str,
        include_classes: Union[List[str], str, None] = None,
        exclude_classes: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
    ) -> dict:
        """
        Restore a backup of all/per class Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : str
            The backend storage from where to restore the backup. Currently available options are:
                "filesystem", "s3", "gcs" and "azure".
            NOTE: Case insensitive.
        include_classes : Union[List[str], str, None], optional
            The class/list of classes to be included in the backup restore. If not specified all
            classes will be included (that were backup-ed). Either `include_classes` or
            `exclude_classes` can be set. By default None.
        exclude_classes : Union[List[str], str, None], optional
            The class/list of classes to be excluded in the backup restore.
            Either `include_classes` or `exclude_classes` can be set. By default None.
        wait_for_completion : bool, optional
            Whether to wait until the backup restore is done.

        Returns
        -------
        dict
            Backup restore response.

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
            include_classes,
            exclude_classes,
        ) = _get_and_validate_create_restore_arguments(
            backup_id=backup_id,
            backend=backend,
            include_classes=include_classes,
            exclude_classes=exclude_classes,
            wait_for_completion=wait_for_completion,
        )

        payload = {
            "config": {},
            "include": include_classes,
            "exclude": exclude_classes,
        }
        path = f"/backups/{backend.value}/{backup_id}/restore"

        try:
            response = self._connection.post(
                path=path,
                weaviate_object=payload,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Backup restore failed due to connection error."
            ) from conn_err
        restore_status = _decode_json_response_dict(response, "Backup restore")
        assert restore_status is not None
        if wait_for_completion:
            while True:
                status: dict = self.get_restore_status(
                    backup_id=backup_id,
                    backend=backend,
                )
                restore_status.update(status)
                if status["status"] == "SUCCESS":
                    break
                if status["status"] == "FAILED":
                    raise BackupFailedException(f"Backup restore failed: {restore_status}")
                sleep(1)
        return restore_status

    def get_restore_status(self, backup_id: str, backend: str) -> Dict[str, Any]:
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
            NOTE: Case insensitive.

        Returns
        -------
        dict
            Status of the backup create.
        """

        backup_id, backend = _get_and_validate_get_status(
            backup_id=backup_id,
            backend=backend,
        )
        path = f"/backups/{backend.value}/{backup_id}/restore"

        try:
            response = self._connection.get(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Backup restore status failed due to connection error."
            ) from conn_err

        typed_response = _decode_json_response_dict(response, "Backup restore status check")
        if typed_response is None:
            raise EmptyResponseException()
        return typed_response


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
