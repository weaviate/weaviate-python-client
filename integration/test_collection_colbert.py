
import weaviate.classes as wvc
from integration.conftest import CollectionFactory


def test_collection_with_colbert_config(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[wvc.config.Property(name="Name", data_type=wvc.config.DataType.TEXT)],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none(

            )
        ]
        wvc.config.Configure.VectorIndex.hnsw(

        ),
    )

    collection.config.get()

