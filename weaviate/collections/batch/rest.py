from typing import Dict, List, Optional

from weaviate.collections.classes.batch import (
    ErrorReference,
    BatchReference,
    _BatchReference,
    BatchReferenceReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect import ConnectionV4
from weaviate.util import _decode_json_response_list

from weaviate.connect.v4 import _ExpectedStatusCodes


class _BatchREST:
    def __init__(
        self, connection: ConnectionV4, consistency_level: Optional[ConsistencyLevel]
    ) -> None:
        self.__connection = connection
        self.__consistency_level = consistency_level

    async def references(self, references: List[_BatchReference]) -> BatchReferenceReturn:
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

        response = await self.__connection.post(
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
                reference=BatchReference._from_internal(references[idx]),
            )
            for idx, entry in enumerate(payload)
            if entry["result"]["status"] == "FAILED"
        }
        return BatchReferenceReturn(
            elapsed_seconds=response.elapsed.total_seconds(),
            errors=errors,
            has_errors=len(errors) > 0,
        )
