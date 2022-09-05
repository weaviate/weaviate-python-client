"""
Backup class definition.
"""
from time import sleep
from typing import Union, List
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    RequestsConnectionError,
    BackupFailedException,
)
from weaviate.util import _capitalize_first_letter
from weaviate.connect import Connection


STORAGE_NAMES = [
    "filesystem",
    "s3",
    "gcs",
]


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

    def create(self,
            backup_id: str,
            storage_name: str,
            include: Union[List[str], str, None]=None,
            exclude: Union[List[str], str, None]=None,
            wait_for_completion: bool=False,
        ) -> dict:
        """
        Create a backup of all/per class Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        storage_name : str
            The storage where to create the backup. Currently available options are:
                "filesystem", "s3" and "gsc".
            NOTE: Case insensitive.
        include : Union[List[str], str, None], optional
            The class/list of classes to be included in the backup. If not specified all classes
            will be included. Either `include` or `exclude` can be set. By default None.
        exclude : Union[List[str], str, None], optional
            The class/list of classes to be excluded in the backup. Either `include` or `exclude`
            can be set. By default None.
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
        """

        if not isinstance(backup_id, str):
            raise TypeError(
                f"'backup_id' must be of type str. Given type: {type(backup_id)}."
            )
        if storage_name not in STORAGE_NAMES:
            raise ValueError(
                f"'storage_name' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {storage_name}."
            )
        if include:
            if isinstance(include, str):
                include = [include]
            elif not isinstance(include, list):
                raise TypeError(
                    "'include' must be of type str, list of str or None. "
                    f"Given type: {type(include)}."
                )
        else:
            include = []

        if exclude:
            if isinstance(exclude, str):
                exclude = [exclude]
            elif not isinstance(exclude, list):
                raise TypeError(
                    "'exclude' must be of type str, list of str or None. "
                    f"Given type: {type(exclude)}."
                )
        else:
            exclude = []

        if include and exclude:
            raise TypeError(
                "Either 'include' OR 'exclude' can be set, not both."
            )

        payload = {
            "id": backup_id.lower(),
            "config": {},
            "include": [_capitalize_first_letter(cls) for cls in include],
            "exclude": [_capitalize_first_letter(cls) for cls in exclude],
        }
        path = f'/backups/{storage_name.lower()}'

        try:
            response = self._connection.post(
                path=path,
                weaviate_object=payload,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                'Backup creation failed due to connection error.'
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Backup creation", response)


        if wait_for_completion:
            while True:
                status = self.get_create_status(
                    backup_id=backup_id,
                    storage_name=storage_name,
                )
                if status['status'] == 'SUCCESS':
                    return status
                if status['status'] == 'FAILED':
                    raise BackupFailedException(f'Backup failed: {status}')
                sleep(1)

        return response.json()

    def get_create_status(self, backup_id: str, storage_name: str) -> bool:
        """
        Checks if a started classification job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        storage_name : str
            The storage where the backup was created. Currently available options are:
                "filesystem", "s3" and "gsc".
            NOTE: Case insensitive.

        Returns
        -------
        dict
            Status of the backup create.
        """

        if not isinstance(backup_id, str):
            raise TypeError(
                f"'backup_id' must be of type str. Given type: {type(backup_id)}."
            )
        if storage_name not in STORAGE_NAMES:
            raise ValueError(
                f"'storage_name' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {storage_name}."
            )

        path = f'/backups/{storage_name.lower()}/{backup_id.lower()}'

        try:
            response = self._connection.get(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                'Backup creation status failed due to connection error.'
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Backup status check", response)
        return response.json()

    def restore(self,
            backup_id: str,
            storage_name: str,
            include: Union[List[str], str, None]=None,
            exclude: Union[List[str], str, None]=None,
            wait_for_completion: bool=False,
        ) -> dict:
        """
        Restore a backup of all/per class Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        storage_name : str
            The storage from where to restore the backup. Currently available options are:
                "filesystem", "s3" and "gsc".
            NOTE: Case insensitive.
        include : Union[List[str], str, None], optional
            The class/list of classes to be included in the backup restore. If not specified all
            classes will be included (that were backup-ed). Either `include` or `exclude` can be
            set. By default None.
        exclude : Union[List[str], str, None], optional
            The class/list of classes to be excluded in the backup restore. Either `include` or
            `exclude` can be set. By default None.
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

        if not isinstance(backup_id, str):
            raise TypeError(
                f"'backup_id' must be of type str. Given type: {type(backup_id)}."
            )
        if storage_name not in STORAGE_NAMES:
            raise ValueError(
                f"'storage_name' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {storage_name}."
            )
        if include:
            if isinstance(include, str):
                include = [include]
            elif not isinstance(include, list):
                raise TypeError(
                    "'include' must be of type str, list of str or None. "
                    f"Given type: {type(include)}."
                )
        else:
            include = []

        if exclude:
            if isinstance(exclude, str):
                exclude = [exclude]
            elif not isinstance(exclude, list):
                raise TypeError(
                    "'exclude' must be of type str, list of str or None. "
                    f"Given type: {type(exclude)}."
                )
        else:
            exclude = []

        if include and exclude:
            raise TypeError(
                "Either 'include' OR 'exclude' can be set, not both."
            )

        payload = {
            "id": backup_id.lower(),
            "config": {},
            "include": [_capitalize_first_letter(cls) for cls in include],
            "exclude": [_capitalize_first_letter(cls) for cls in exclude],
        }
        path = f'/backups/{storage_name.lower()}/{backup_id.lower()}/restore'

        try:
            response = self._connection.post(
                path=path,
                weaviate_object=payload,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                'Backup restore failed due to connection error.'
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Backup restore", response)

        if wait_for_completion:
            while True:
                status = self.get_restore_status(
                    backup_id=backup_id,
                    storage_name=storage_name,
                )
                if status['status'] == 'SUCCESS':
                    return status
                if status['status'] == 'FAILED':
                    raise BackupFailedException(f'Backup restore failed: {status}')
                sleep(1)

        return response.json()

    def get_restore_status(self, backup_id: str, storage_name: str) -> bool:
        """
        Checks if a started classification job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        storage_name : str
            The Storage where to create the backup. Currently available options are:
                "filesystem", "s3" and "gsc".
            NOTE: Case insensitive.

        Returns
        -------
        dict
            Status of the backup create.
        """

        if not isinstance(backup_id, str):
            raise TypeError(
                f"'backup_id' must be of type str. Given type: {type(backup_id)}."
            )
        if storage_name not in STORAGE_NAMES:
            raise ValueError(
                f"'storage_name' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {storage_name}."
            )

        path = f'/backups/{storage_name.lower()}/{backup_id.lower()}/restore'

        try:
            response = self._connection.get(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                'Backup restore status failed due to connection error.'
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Backup restore status check", response)
        return response.json()
