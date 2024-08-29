from weaviate.collections.classes.config import Configure


def test_multi2vec_clip() -> None:
    Configure.Vectorizer.multi2vec_clip(image_fields=["test"])
