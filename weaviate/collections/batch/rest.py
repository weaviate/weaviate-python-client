from typing import Dict, List, Optional

from httpx import Response

from weaviate.collections.classes.batch import (
    ErrorReference,
    BatchReference,
    _BatchReference,
    BatchReferenceReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect import executor
from weaviate.connect.v4 import Connection, _ExpectedStatusCodes
from weaviate.util import _decode_json_response_list


class _BatchREST:
    def __init__(self, consistency_level: Optional[ConsistencyLevel]) -> None:
        self.__consistency_level = consistency_level

    def references(
        self, connection: Connection, *, references: List[_BatchReference]
    ) -> executor.Result[BatchReferenceReturn]:
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

        def resp(res: Response) -> BatchReferenceReturn:
            payload = _decode_json_response_list(res, "batch ref")
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
                elapsed_seconds=res.elapsed.total_seconds(),
                errors=errors,
                has_errors=len(errors) > 0,
            )

        return executor.execute(
            response_callback=resp,
            method=connection.post,
            path="/batch/references",
            weaviate_object=refs,
            params=params,
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Send ref batch"),
        )
