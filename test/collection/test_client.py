import pytest
import weaviate

from weaviate.exceptions import WeaviateInvalidInputError


def test_client_no_connection_params_nor_embedded_options() -> None:
    with pytest.raises(TypeError):
        weaviate.client.WeaviateClient()


def test_client_both_connection_params_and_embedded_options() -> None:
    with pytest.raises(TypeError):
        weaviate.client.WeaviateClient(
            connection_params=weaviate.connect.ConnectionParams.from_url(
                "http://localhost:8080", 50051
            ),
            embedded_options=weaviate.embedded.EmbeddedOptions(),
        )


def test_client_bad_connection_params() -> None:
    with pytest.raises(TypeError):
        weaviate.client.WeaviateClient(connection_params="http://localhost:8080")


def test_client_bad_embedded_options() -> None:
    with pytest.raises(WeaviateInvalidInputError):
        weaviate.client.WeaviateClient(embedded_options="bad")


def test_connect_to_wcs_failes_with_null_cluster_url() -> None:
    with pytest.raises(WeaviateInvalidInputError):
        weaviate.connect_to_wcs(None, None)  # type: ignore
