"""Export class definition."""

import asyncio
import time
from typing import Dict, Generic, List, Optional, Tuple, Union

from httpx import Response

from weaviate.connect import executor
from weaviate.connect.v4 import (
    Connection,
    ConnectionAsync,
    ConnectionType,
    _ExpectedStatusCodes,
)
from weaviate.exceptions import (
    EmptyResponseException,
    ExportCancelledError,
    ExportFailedError,
)
from weaviate.export.export import (
    STORAGE_NAMES,
    ExportConfig,
    ExportCreateReturn,
    ExportFileFormat,
    ExportStatus,
    ExportStatusReturn,
    ExportStorage,
)
from weaviate.util import (
    _capitalize_first_letter,
    _decode_json_response_dict,
)


class _ExportExecutor(Generic[ConnectionType]):
    def __init__(self, connection: Connection):
        self._connection = connection

    def create(
        self,
        export_id: str,
        backend: ExportStorage,
        file_format: ExportFileFormat,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[ExportConfig] = None,
    ) -> executor.Result[ExportCreateReturn]:
        """Create an export of all/per collection Weaviate objects.

        Args:
            export_id: The identifier name of the export.
            backend: The backend storage where to create the export.
            file_format: The file format of the export (e.g. ExportFileFormat.PARQUET).
            include_collections: The collection/list of collections to be included in the export. If not specified all
                collections will be included. Either `include_collections` or `exclude_collections` can be set.
            exclude_collections: The collection/list of collections to be excluded in the export.
                Either `include_collections` or `exclude_collections` can be set.
            wait_for_completion: Whether to wait until the export is done. By default False.
            config: The configuration of the export (bucket, path). By default None.

        Returns:
            An `ExportCreateReturn` object that contains the export creation response.

        Raises:
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a non-OK status.
            TypeError: One of the arguments have a wrong type.
        """
        (
            export_id,
            backend,
            include_collections,
            exclude_collections,
        ) = _get_and_validate_create_arguments(
            export_id=export_id,
            backend=backend,
            include_classes=include_collections,
            exclude_classes=exclude_collections,
            wait_for_completion=wait_for_completion,
        )

        payload: dict = {
            "id": export_id,
            "file_format": file_format.value,
            "include": include_collections,
            "exclude": exclude_collections,
        }

        if config is not None:
            config_dict: Dict[str, str] = {}
            if config.bucket is not None:
                config_dict["bucket"] = config.bucket
            if config.path is not None:
                config_dict["path"] = config.path
            if config_dict:
                payload["config"] = config_dict

        path = f"/export/{backend.value}"

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> ExportCreateReturn:
                res = await executor.aresult(
                    self._connection.post(
                        path=path,
                        weaviate_object=payload,
                        error_msg="Export creation failed due to connection error.",
                    )
                )
                create_status = _decode_json_response_dict(res, "Export creation")
                assert create_status is not None
                if wait_for_completion:
                    while True:
                        status = await executor.aresult(
                            self.get_status(
                                export_id=export_id,
                                backend=backend,
                                bucket=config.bucket if config else None,
                                path=config.path if config else None,
                            )
                        )
                        create_status["status"] = status.status
                        if status.status == ExportStatus.SUCCESS:
                            break
                        if status.status == ExportStatus.FAILED:
                            raise ExportFailedError(
                                f"Export failed: {create_status} with error: {status.error}"
                            )
                        if status.status == ExportStatus.CANCELLED:
                            raise ExportCancelledError(
                                f"Export was cancelled: {create_status} with error: {status.error}"
                            )
                        await asyncio.sleep(1)
                return ExportCreateReturn(**create_status)

            return _execute()

        res = executor.result(
            self._connection.post(
                path=path,
                weaviate_object=payload,
                error_msg="Export creation failed due to connection error.",
            )
        )
        create_status = _decode_json_response_dict(res, "Export creation")
        assert create_status is not None
        if wait_for_completion:
            while True:
                status = executor.result(
                    self.get_status(
                        export_id=export_id,
                        backend=backend,
                        bucket=config.bucket if config else None,
                        path=config.path if config else None,
                    )
                )
                create_status["status"] = status.status
                if status.status == ExportStatus.SUCCESS:
                    break
                if status.status == ExportStatus.FAILED:
                    raise ExportFailedError(
                        f"Export failed: {create_status} with error: {status.error}"
                    )
                if status.status == ExportStatus.CANCELLED:
                    raise ExportCancelledError(
                        f"Export was cancelled: {create_status} with error: {status.error}"
                    )
                time.sleep(1)
        return ExportCreateReturn(**create_status)

    def get_status(
        self,
        export_id: str,
        backend: ExportStorage,
        bucket: Optional[str] = None,
        path: Optional[str] = None,
    ) -> executor.Result[ExportStatusReturn]:
        """Check the status of an export.

        Args:
            export_id: The identifier name of the export.
            backend: The backend storage where the export was created.
            bucket: The bucket of the export location. By default None.
            path: The path of the export location. By default None.

        Returns:
            An `ExportStatusReturn` object that contains the export status response.
        """
        export_id, backend = _get_and_validate_get_status(
            export_id=export_id,
            backend=backend,
        )

        url_path = f"/export/{backend.value}/{export_id}"
        params: Dict[str, str] = {}
        if bucket is not None:
            params["bucket"] = bucket
        if path is not None:
            params["path"] = path

        def resp(res: Response) -> ExportStatusReturn:
            typed_response = _decode_json_response_dict(res, "Export status check")
            if typed_response is None:
                raise EmptyResponseException()
            return ExportStatusReturn(**typed_response)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=url_path,
            params=params,
            error_msg="Export status check failed due to connection error.",
        )

    def cancel(
        self,
        export_id: str,
        backend: ExportStorage,
        bucket: Optional[str] = None,
        path: Optional[str] = None,
    ) -> executor.Result[bool]:
        """Cancel a running export.

        Args:
            export_id: The identifier name of the export.
            backend: The backend storage where the export was created.
            bucket: The bucket of the export location. By default None.
            path: The path of the export location. By default None.

        Returns:
            A bool indicating if the cancellation was successful.
        """
        export_id, backend = _get_and_validate_get_status(
            export_id=export_id,
            backend=backend,
        )
        url_path = f"/export/{backend.value}/{export_id}"
        params: Dict[str, str] = {}
        if bucket is not None:
            params["bucket"] = bucket
        if path is not None:
            params["path"] = path

        def resp(res: Response) -> bool:
            if res.status_code == 204:
                return True
            typed_response = _decode_json_response_dict(res, "Export cancel")
            if typed_response is None:
                raise EmptyResponseException()
            return False

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=url_path,
            params=params,
            error_msg="Export cancel failed due to connection error.",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="cancel export"),
        )


def _get_and_validate_create_arguments(
    export_id: str,
    backend: Union[str, ExportStorage],
    include_classes: Union[List[str], str, None],
    exclude_classes: Union[List[str], str, None],
    wait_for_completion: bool,
) -> Tuple[str, ExportStorage, List[str], List[str]]:
    if not isinstance(export_id, str):
        raise TypeError(f"'export_id' must be of type str. Given type: {type(export_id)}.")
    if isinstance(backend, str):
        try:
            backend = ExportStorage(backend.lower())
        except KeyError:
            raise ValueError(
                f"'backend' must have one of these values: {STORAGE_NAMES}. Given value: {backend}."
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
                "'include_collections' must be of type str, list of str or None. "
                f"Given type: {type(include_classes)}."
            )
    else:
        include_classes = []

    if exclude_classes is not None:
        if isinstance(exclude_classes, str):
            exclude_classes = [exclude_classes]
        elif not isinstance(exclude_classes, list):
            raise TypeError(
                "'exclude_collections' must be of type str, list of str or None. "
                f"Given type: {type(exclude_classes)}."
            )
    else:
        exclude_classes = []

    if include_classes and exclude_classes:
        raise TypeError(
            "Either 'include_collections' OR 'exclude_collections' can be set, not both."
        )

    include_classes = [_capitalize_first_letter(cls) for cls in include_classes]
    exclude_classes = [_capitalize_first_letter(cls) for cls in exclude_classes]

    return (export_id, backend, include_classes, exclude_classes)


def _get_and_validate_get_status(
    export_id: str, backend: Union[str, ExportStorage]
) -> Tuple[str, ExportStorage]:
    if not isinstance(export_id, str):
        raise TypeError(f"'export_id' must be of type str. Given type: {type(export_id)}.")
    if isinstance(backend, str):
        try:
            backend = ExportStorage(backend.lower())
        except KeyError:
            raise ValueError(
                f"'backend' must have one of these values: {STORAGE_NAMES}. Given value: {backend}."
            )

    return (export_id, backend)
