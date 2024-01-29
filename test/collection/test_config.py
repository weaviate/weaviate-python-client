from typing import List

import pytest
from pydantic import ValidationError

from weaviate.collections.classes.config import (
    _CollectionConfigCreate,
    DataType,
    Multi2VecField,
    _GenerativeConfigCreate,
    _RerankerConfigCreate,
    _VectorizerConfigCreate,
    Configure,
    Property,
    ReferenceProperty,
    VectorDistances,
)

DEFAULTS = {
    "vectorizer": "none",
    "vectorIndexType": "hnsw",
}


def test_basic_config():
    config = _CollectionConfigCreate(
        name="test",
        description="test",
    )
    assert config._to_dict() == {
        **DEFAULTS,
        "class": "Test",
        "description": "test",
    }


TEST_CONFIG_WITH_VECTORIZER_PARAMETERS = [
    (
        Configure.Vectorizer.text2vec_contextionary(),
        {
            "text2vec-contextionary": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_azure_openai(
            resource_name="resource",
            deployment_id="deployment",
            base_url="https://api.openai.com",
        ),
        {
            "text2vec-openai": {
                "resourceName": "resource",
                "deploymentId": "deployment",
                "vectorizeClassName": True,
                "baseURL": "https://api.openai.com/",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_cohere(),
        {
            "text2vec-cohere": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_cohere(
            model="embed-multilingual-v2.0",
            truncate="NONE",
            vectorize_collection_name=False,
            base_url="https://api.cohere.ai",
        ),
        {
            "text2vec-cohere": {
                "model": "embed-multilingual-v2.0",
                "truncate": "NONE",
                "vectorizeClassName": False,
                "baseURL": "https://api.cohere.ai/",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_gpt4all(),
        {
            "text2vec-gpt4all": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_gpt4all(
            vectorize_collection_name=False,
        ),
        {
            "text2vec-gpt4all": {
                "vectorizeClassName": False,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_huggingface(
            model="model", wait_for_model=False, use_gpu=False, use_cache=False
        ),
        {
            "text2vec-huggingface": {
                "options": {
                    "waitForModel": False,
                    "useGPU": False,
                    "useCache": False,
                },
                "model": "model",
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_huggingface(
            passage_model="passageModel",
            query_model="queryModel",
            wait_for_model=True,
            use_gpu=True,
            use_cache=True,
            vectorize_collection_name=False,
        ),
        {
            "text2vec-huggingface": {
                "options": {
                    "waitForModel": True,
                    "useGPU": True,
                    "useCache": True,
                },
                "passageModel": "passageModel",
                "queryModel": "queryModel",
                "vectorizeClassName": False,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_huggingface(
            endpoint_url="https://api.huggingface.co",
        ),
        {
            "text2vec-huggingface": {
                "endpointURL": "https://api.huggingface.co/",
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_aws(
            vectorize_collection_name=False, model="cohere.embed-english-v3", region="us-east-1"
        ),
        {
            "text2vec-aws": {
                "vectorizeClassName": False,
                "model": "cohere.embed-english-v3",
                "region": "us-east-1",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_openai(),
        {
            "text2vec-openai": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_openai(
            vectorize_collection_name=False,
            model="ada",
            model_version="002",
            type_="text",
            base_url="https://api.openai.com",
        ),
        {
            "text2vec-openai": {
                "vectorizeClassName": False,
                "model": "ada",
                "modelVersion": "002",
                "type": "text",
                "baseURL": "https://api.openai.com/",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_palm(
            project_id="project",
        ),
        {
            "text2vec-palm": {
                "projectId": "project",
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_palm(
            project_id="project",
            api_endpoint="https://api.google.com",
            model_id="model",
            vectorize_collection_name=False,
        ),
        {
            "text2vec-palm": {
                "projectId": "project",
                "apiEndpoint": "https://api.google.com/",
                "modelId": "model",
                "vectorizeClassName": False,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_transformers(),
        {
            "text2vec-transformers": {
                "vectorizeClassName": True,
                "poolingStrategy": "masked_mean",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_transformers(
            pooling_strategy="cls",
            vectorize_collection_name=False,
        ),
        {
            "text2vec-transformers": {
                "vectorizeClassName": False,
                "poolingStrategy": "cls",
            }
        },
    ),
    (
        Configure.Vectorizer.img2vec_neural(
            image_fields=["test"],
        ),
        {
            "img2vec-neural": {
                "imageFields": ["test"],
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_clip(
            image_fields=["image"],
            text_fields=["text"],
        ),
        {
            "multi2vec-clip": {
                "imageFields": ["image"],
                "textFields": ["text"],
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_clip(
            image_fields=[Multi2VecField(name="image")],
            text_fields=[Multi2VecField(name="text")],
        ),
        {
            "multi2vec-clip": {
                "imageFields": ["image"],
                "textFields": ["text"],
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_clip(
            image_fields=[Multi2VecField(name="image", weight=0.5)],
            text_fields=[Multi2VecField(name="text", weight=0.5)],
            vectorize_collection_name=False,
        ),
        {
            "multi2vec-clip": {
                "imageFields": ["image"],
                "textFields": ["text"],
                "vectorizeClassName": False,
                "weights": {
                    "imageFields": [0.5],
                    "textFields": [0.5],
                },
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_bind(
            audio_fields=["audio"],
            depth_fields=["depth"],
            image_fields=["image"],
            imu_fields=["imu"],
            text_fields=["text"],
            thermal_fields=["thermal"],
        ),
        {
            "multi2vec-bind": {
                "audioFields": ["audio"],
                "depthFields": ["depth"],
                "imageFields": ["image"],
                "IMUFields": ["imu"],
                "textFields": ["text"],
                "thermalFields": ["thermal"],
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_bind(
            audio_fields=[Multi2VecField(name="audio")],
            depth_fields=[Multi2VecField(name="depth")],
            image_fields=[Multi2VecField(name="image")],
            imu_fields=[Multi2VecField(name="imu")],
            text_fields=[Multi2VecField(name="text")],
            thermal_fields=[Multi2VecField(name="thermal")],
        ),
        {
            "multi2vec-bind": {
                "audioFields": ["audio"],
                "depthFields": ["depth"],
                "imageFields": ["image"],
                "IMUFields": ["imu"],
                "textFields": ["text"],
                "thermalFields": ["thermal"],
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_bind(
            audio_fields=[Multi2VecField(name="audio", weight=0.5)],
            depth_fields=[Multi2VecField(name="depth", weight=0.5)],
            image_fields=[Multi2VecField(name="image", weight=0.5)],
            imu_fields=[Multi2VecField(name="imu", weight=0.5)],
            text_fields=[Multi2VecField(name="text", weight=0.5)],
            thermal_fields=[Multi2VecField(name="thermal", weight=0.5)],
            vectorize_collection_name=False,
        ),
        {
            "multi2vec-bind": {
                "audioFields": ["audio"],
                "depthFields": ["depth"],
                "imageFields": ["image"],
                "IMUFields": ["imu"],
                "textFields": ["text"],
                "thermalFields": ["thermal"],
                "vectorizeClassName": False,
                "weights": {
                    "audioFields": [0.5],
                    "depthFields": [0.5],
                    "imageFields": [0.5],
                    "IMUFields": [0.5],
                    "textFields": [0.5],
                    "thermalFields": [0.5],
                },
            }
        },
    ),
    (
        Configure.Vectorizer.ref2vec_centroid(reference_properties=["prop"]),
        {"ref2vec-centroid": {"referenceProperties": ["prop"], "method": "mean"}},
    ),
]


@pytest.mark.parametrize("vectorizer_config,expected", TEST_CONFIG_WITH_VECTORIZER_PARAMETERS)
def test_config_with_module(vectorizer_config: _VectorizerConfigCreate, expected: dict):
    config = _CollectionConfigCreate(name="test", vectorizer_config=vectorizer_config)
    assert config._to_dict() == {
        **DEFAULTS,
        "vectorizer": vectorizer_config.vectorizer.value,
        "class": "Test",
        "moduleConfig": expected,
    }


TEST_CONFIG_WITH_VECTORIZER_AND_PROPERTIES_PARAMETERS = [
    (
        Configure.Vectorizer.text2vec_transformers(),
        [
            Property(
                name="text",
                data_type=DataType.TEXT,
                skip_vectorization=True,
                vectorize_property_name=False,
            )
        ],
        {
            "text2vec-transformers": {
                "vectorizeClassName": True,
                "poolingStrategy": "masked_mean",
            }
        },
        [
            {
                "dataType": ["text"],
                "name": "text",
                "moduleConfig": {
                    "text2vec-transformers": {
                        "skip": True,
                        "vectorizePropertyName": False,
                    }
                },
            }
        ],
    ),
    (
        Configure.Vectorizer.text2vec_jinaai(),
        [
            Property(
                name="text",
                data_type=DataType.TEXT,
                skip_vectorization=True,
                vectorize_property_name=False,
            )
        ],
        {
            "text2vec-jinaai": {
                "vectorizeClassName": True,
            }
        },
        [
            {
                "dataType": ["text"],
                "name": "text",
                "moduleConfig": {
                    "text2vec-jinaai": {
                        "skip": True,
                        "vectorizePropertyName": False,
                    }
                },
            }
        ],
    ),
    (
        Configure.Vectorizer.text2vec_transformers(),
        [
            Property(
                name="text",
                data_type=DataType.TEXT,
            )
        ],
        {
            "text2vec-transformers": {
                "vectorizeClassName": True,
                "poolingStrategy": "masked_mean",
            }
        },
        [
            {
                "dataType": ["text"],
                "name": "text",
                "moduleConfig": {
                    "text2vec-transformers": {
                        "skip": False,
                        "vectorizePropertyName": True,
                    }
                },
            }
        ],
    ),
]


@pytest.mark.parametrize(
    "vectorizer_config,properties,expected_mc,expected_props",
    TEST_CONFIG_WITH_VECTORIZER_AND_PROPERTIES_PARAMETERS,
)
def test_config_with_vectorizer_and_properties(
    vectorizer_config: _VectorizerConfigCreate,
    properties: List[Property],
    expected_mc: dict,
    expected_props: dict,
) -> None:
    config = _CollectionConfigCreate(
        name="test", properties=properties, vectorizer_config=vectorizer_config
    )
    assert config._to_dict() == {
        **DEFAULTS,
        "vectorizer": vectorizer_config.vectorizer.value,
        "class": "Test",
        "properties": expected_props,
        "moduleConfig": expected_mc,
    }


TEST_CONFIG_WITH_GENERATIVE = [
    (
        Configure.Generative.openai(),
        {"generative-openai": {}},
    ),
    (
        Configure.Generative.anyscale(),
        {"generative-anyscale": {}},
    ),
    (
        Configure.Generative.openai(
            model="gpt-4",
            frequency_penalty=0.5,
            max_tokens=100,
            presence_penalty=0.5,
            temperature=0.5,
            top_p=0.5,
            base_url="https://api.openai.com",
        ),
        {
            "generative-openai": {
                "model": "gpt-4",
                "frequencyPenaltyProperty": 0.5,
                "maxTokensProperty": 100,
                "presencePenaltyProperty": 0.5,
                "temperatureProperty": 0.5,
                "topPProperty": 0.5,
                "baseURL": "https://api.openai.com/",
            }
        },
    ),
    (Configure.Generative.cohere(), {"generative-cohere": {}}),
    (
        Configure.Generative.cohere(
            model="model",
            k=10,
            max_tokens=100,
            return_likelihoods="ALL",
            stop_sequences=["stop"],
            temperature=0.5,
            base_url="https://api.cohere.ai",
        ),
        {
            "generative-cohere": {
                "model": "model",
                "kProperty": 10,
                "maxTokensProperty": 100,
                "returnLikelihoodsProperty": "ALL",
                "stopSequencesProperty": ["stop"],
                "temperatureProperty": 0.5,
                "baseURL": "https://api.cohere.ai/",
            }
        },
    ),
    (
        Configure.Generative.palm(project_id="project"),
        {
            "generative-palm": {
                "projectId": "project",
            }
        },
    ),
    (
        Configure.Generative.palm(
            project_id="project",
            api_endpoint="https://api.google.com",
            max_output_tokens=100,
            model_id="model",
            temperature=0.5,
            top_k=10,
            top_p=0.5,
        ),
        {
            "generative-palm": {
                "projectId": "project",
                "apiEndpoint": "https://api.google.com/",
                "maxOutputTokens": 100,
                "modelId": "model",
                "temperature": 0.5,
                "topK": 10,
                "topP": 0.5,
            }
        },
    ),
    (
        Configure.Generative.aws(model="cohere.command-light-text-v14", region="us-east-1"),
        {
            "generative-aws": {
                "model": "cohere.command-light-text-v14",
                "region": "us-east-1",
            }
        },
    ),
]


@pytest.mark.parametrize(
    "generative_config,expected_mc",
    TEST_CONFIG_WITH_GENERATIVE,
)
def test_config_with_generative(
    generative_config: _GenerativeConfigCreate,
    expected_mc: dict,
):
    config = _CollectionConfigCreate(name="test", generative_config=generative_config)
    assert config._to_dict() == {
        **DEFAULTS,
        "vectorizer": "none",
        "class": "Test",
        "moduleConfig": expected_mc,
    }


TEST_CONFIG_WITH_RERANKER = [
    (
        Configure.Reranker.cohere(model="model"),
        {
            "reranker-cohere": {
                "model": "model",
            },
        },
    ),
    (
        Configure.Reranker.cohere(),
        {
            "reranker-cohere": {},
        },
    ),
    (
        Configure.Reranker.transformers(),
        {
            "reranker-transformers": {},
        },
    ),
]


@pytest.mark.parametrize("reranker_config,expected_mc", TEST_CONFIG_WITH_RERANKER)
def test_config_with_reranker(
    reranker_config: _RerankerConfigCreate,
    expected_mc: dict,
):
    config = _CollectionConfigCreate(name="test", reranker_config=reranker_config)
    assert config._to_dict() == {
        **DEFAULTS,
        "vectorizer": "none",
        "class": "Test",
        "moduleConfig": expected_mc,
    }


def test_config_with_properties():
    config = _CollectionConfigCreate(
        name="test",
        description="test",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(
                name="text",
                data_type=DataType.TEXT,
            ),
            Property(
                name="text_array",
                data_type=DataType.TEXT_ARRAY,
            ),
            Property(
                name="int",
                data_type=DataType.INT,
            ),
            Property(
                name="int_array",
                data_type=DataType.INT_ARRAY,
            ),
            Property(
                name="number",
                data_type=DataType.NUMBER,
            ),
            Property(
                name="number_array",
                data_type=DataType.NUMBER_ARRAY,
            ),
            Property(
                name="bool",
                data_type=DataType.BOOL,
            ),
            Property(
                name="bool_array",
                data_type=DataType.BOOL_ARRAY,
            ),
            Property(
                name="date",
                data_type=DataType.DATE,
            ),
            Property(
                name="date_array",
                data_type=DataType.DATE_ARRAY,
            ),
            Property(
                name="uuid",
                data_type=DataType.UUID,
            ),
            Property(
                name="uuid_array",
                data_type=DataType.UUID_ARRAY,
            ),
            Property(
                name="geo",
                data_type=DataType.GEO_COORDINATES,
            ),
            Property(
                name="blob",
                data_type=DataType.BLOB,
            ),
            Property(
                name="phone_number",
                data_type=DataType.PHONE_NUMBER,
            ),
        ],
    )
    assert config._to_dict() == {
        **DEFAULTS,
        "class": "Test",
        "description": "test",
        "properties": [
            {
                "dataType": ["text"],
                "name": "text",
            },
            {
                "dataType": ["text[]"],
                "name": "text_array",
            },
            {
                "dataType": ["int"],
                "name": "int",
            },
            {
                "dataType": ["int[]"],
                "name": "int_array",
            },
            {
                "dataType": ["number"],
                "name": "number",
            },
            {
                "dataType": ["number[]"],
                "name": "number_array",
            },
            {
                "dataType": ["boolean"],
                "name": "bool",
            },
            {
                "dataType": ["boolean[]"],
                "name": "bool_array",
            },
            {
                "dataType": ["date"],
                "name": "date",
            },
            {
                "dataType": ["date[]"],
                "name": "date_array",
            },
            {
                "dataType": ["uuid"],
                "name": "uuid",
            },
            {
                "dataType": ["uuid[]"],
                "name": "uuid_array",
            },
            {
                "dataType": ["geoCoordinates"],
                "name": "geo",
            },
            {
                "dataType": ["blob"],
                "name": "blob",
            },
            {
                "dataType": ["phoneNumber"],
                "name": "phone_number",
            },
        ],
    }


@pytest.mark.parametrize("name", ["id", "vector"])
def test_config_with_invalid_property(name: str):
    with pytest.raises(ValidationError):
        _CollectionConfigCreate(
            name="test",
            description="test",
            properties=[Property(name=name, data_type=DataType.TEXT)],
        )


@pytest.mark.parametrize("name", ["id", "vector"])
def test_config_with_invalid_reference_property(name: str):
    with pytest.raises(ValidationError):
        _CollectionConfigCreate(
            name="test", description="test", properties=[ReferenceProperty(name=name, to="Test")]
        )


def test_vector_config_hnsw_bq() -> None:
    vector_index = Configure.VectorIndex.hnsw(
        ef_construction=128, quantizer=Configure.VectorIndex.Quantizer.bq(rescore_limit=123)
    )

    vi_dict = vector_index._to_dict()

    assert vi_dict["efConstruction"] == 128
    assert vi_dict["bq"]["rescoreLimit"] == 123


def test_vector_config_flat_pq() -> None:
    vector_index = Configure.VectorIndex.flat(
        distance_metric=VectorDistances.DOT,
        vector_cache_max_objects=456,
        quantizer=Configure.VectorIndex.Quantizer.pq(bit_compression=True, segments=789),
    )

    vi_dict = vector_index._to_dict()

    assert vi_dict["distance"] == "dot"
    assert vi_dict["vectorCacheMaxObjects"] == 456
    assert vi_dict["pq"]["bitCompression"]
    assert vi_dict["pq"]["segments"] == 789
