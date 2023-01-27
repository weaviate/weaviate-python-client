from typing import Optional

import pytest

import weaviate
from requests.exceptions import ConnectionError as RequestsConnectionError


@pytest.mark.parametrize("wait_for_weaviate", [1, None])
def test_wait_for_weaviate_Error(wait_for_weaviate: Optional[int]):
    WRONG_ADDRESS = "http://localhost:15623"
    with pytest.raises(RequestsConnectionError):
        weaviate.Client(url=WRONG_ADDRESS, wait_for_weaviate=wait_for_weaviate)
