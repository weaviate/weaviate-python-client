from typing import Dict, List, Optional

from weaviate.collections.classes.batch import (
    ErrorReference,
    _BatchReference,
    BatchReferenceReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect import ConnectionV4
from weaviate.exceptions import UnexpectedStatusCodeError
from weaviate.util import _decode_json_response_list

from weaviate.connect.v4 import _ExpectedStatusCodes


class _BatchREST:
    def __init__(
        self, connection: ConnectionV4, consistency_level: Optional[ConsistencyLevel]
    ) -> None:
        self.__connection = connection
        self.__consistency_level = consistency_level

    def references(self, references: List[_BatchReference]) -> BatchReferenceReturn:
        params: Dict[str, str] = {}
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level.value

        refs = [
            (
                {"from": ref.from_, "to": ref.to}
                if ref.tenant is None
                else {"from": ref.from_, "to": ref.to, "tenant": ref.tenant}
            )
            for ref in references
        ]

        response = self.__connection.post(
            path="/batch/references",
            weaviate_object=refs,
            params=params,
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Send ref batch"),
        )

        payload = _decode_json_response_list(response, "batch ref")
        assert payload is not None
        errors = {
            idx: ErrorReference(
                message=entry["result"]["errors"]["error"][0]["message"],
                reference=references[idx],
            )
            for idx, entry in enumerate(payload)
            if entry["result"]["status"] == "FAILED"
        }
        return BatchReferenceReturn(
            elapsed_seconds=response.elapsed.total_seconds(),
            errors=errors,
            has_errors=len(errors) > 0,
        )


class _BatchRESTAsync:
    def __init__(
        self, connection: ConnectionV4, consistency_level: Optional[ConsistencyLevel]
    ) -> None:
        self.__consistency_level = consistency_level
        self.__connection = connection

    async def references(self, references: List[_BatchReference]) -> BatchReferenceReturn:
        params: Dict[str, str] = {}
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level

        refs = [
            (
                {"from": ref.from_, "to": ref.to}
                if ref.tenant is None
                else {"from": ref.from_, "to": ref.to, "tenant": ref.tenant}
            )
            for ref in references
        ]

        response = await self.__connection.apost(
            path="/batch/references", weaviate_object=refs, params=params
        )
        if response.status_code == 200:
            payload = response.json()
            errors = {
                idx: ErrorReference(
                    message=entry["result"]["errors"]["error"][0]["message"],
                    reference=references[idx],
                )
                for idx, entry in enumerate(payload)
                if entry["result"]["status"] == "FAILED"
            }
            return BatchReferenceReturn(
                elapsed_seconds=response.elapsed.total_seconds(),
                errors=errors,
                has_errors=len(errors) > 0,
            )
        raise UnexpectedStatusCodeError("Send ref batch", response)
