import pytest
from weaviate.collections.classes.config import Configure


def test_multi2vec_clip() -> None:
    cfg = Configure.Vectorizer.multi2vec_clip(image_fields=["test"], vectorize_collection_name=False)
    assert cfg._to_dict()["vectorizeClassName"] is False


@pytest.mark.parametrize(
    "vectorize_collection_name", [True, False]
)
def test_multi2vec_vectorize_collection_name(vectorize_collection_name: bool) -> None:
    clip_cfg = Configure.Vectorizer.multi2vec_clip(vectorize_collection_name=vectorize_collection_name)
    assert clip_cfg._to_dict()["vectorizeClassName"] == vectorize_collection_name

    bind_cfg = Configure.Vectorizer.multi2vec_bind(vectorize_collection_name=vectorize_collection_name)
    assert bind_cfg._to_dict()["vectorizeClassName"] == vectorize_collection_name

    cohere_cfg = Configure.Vectorizer.multi2vec_cohere(vectorize_collection_name=vectorize_collection_name)
    assert cohere_cfg._to_dict()["vectorizeClassName"] == vectorize_collection_name

    voyage_cfg = Configure.Vectorizer.multi2vec_voyageai(
        output_encoding="base64", vectorize_collection_name=vectorize_collection_name
    )
    assert voyage_cfg._to_dict()["vectorizeClassName"] == vectorize_collection_name

    nvidia_cfg = Configure.Vectorizer.multi2vec_nvidia(vectorize_collection_name=vectorize_collection_name)
    assert nvidia_cfg._to_dict()["vectorizeClassName"] == vectorize_collection_name

    jina_cfg = Configure.Vectorizer.multi2vec_jinaai(vectorize_collection_name=vectorize_collection_name)
    assert jina_cfg._to_dict()["vectorizeClassName"] == vectorize_collection_name
