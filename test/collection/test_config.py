import pytest
from typing import List
from weaviate.collection.classes.config import (
    CollectionConfigCreate,
    DataType,
    Multi2VecField,
    VectorizerConfig,
    VectorizerFactory,
    Property,
    PropertyVectorizerConfig,
    Vectorizer,
)


DEFAULTS = {
    "vectorizer": "none",
    "vectorIndexType": "hnsw",
}


def test_basic_config():
    config = CollectionConfigCreate(
        name="test",
        description="test",
    )
    assert config.to_dict() == {
        **DEFAULTS,
        "class": "Test",
        "description": "test",
    }


TEST_CONFIG_WITH_MODULE_PARAMETERS = [
    (
        VectorizerFactory.text2vec_contextionary(),
        {
            "text2vec-contextionary": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        VectorizerFactory.text2vec_azure_openai(
            resource_name="resource",
            deployment_id="deployment",
        ),
        {
            "text2vec-openai": {
                "resourceName": "resource",
                "deploymentId": "deployment",
            }
        },
    ),
    (
        VectorizerFactory.text2vec_cohere(),
        {"text2vec-cohere": {}},
    ),
    (
        VectorizerFactory.text2vec_cohere(model="embed-multilingual-v2.0", truncate="NONE"),
        {"text2vec-cohere": {"model": "embed-multilingual-v2.0", "truncate": "NONE"}},
    ),
    (
        VectorizerFactory.text2vec_gpt4all(),
        {
            "text2vec-gpt4all": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        VectorizerFactory.text2vec_gpt4all(
            vectorize_class_name=False,
        ),
        {
            "text2vec-gpt4all": {
                "vectorizeClassName": False,
            }
        },
    ),
    (
        VectorizerFactory.text2vec_huggingface(
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
            }
        },
    ),
    (
        VectorizerFactory.text2vec_huggingface(
            passage_model="passageModel",
            query_model="queryModel",
            wait_for_model=True,
            use_gpu=True,
            use_cache=True,
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
            }
        },
    ),
    (
        VectorizerFactory.text2vec_huggingface(
            endpoint_url="endpoint",
        ),
        {
            "text2vec-huggingface": {
                "endpointURL": "endpoint",
            }
        },
    ),
    (
        VectorizerFactory.text2vec_openai(),
        {
            "text2vec-openai": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        VectorizerFactory.text2vec_openai(
            vectorize_class_name=False,
            model="ada",
            model_version="002",
            type_="text",
        ),
        {
            "text2vec-openai": {
                "vectorizeClassName": False,
                "model": "ada",
                "modelVersion": "002",
                "type": "text",
            }
        },
    ),
    (
        VectorizerFactory.text2vec_palm(
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
        VectorizerFactory.text2vec_palm(
            project_id="project",
            api_endpoint="https://weaviate.io",
            model_id="model",
            vectorize_class_name=False,
        ),
        {
            "text2vec-palm": {
                "projectId": "project",
                "apiEndpoint": "https://weaviate.io/",
                "modelId": "model",
                "vectorizeClassName": False,
            }
        },
    ),
    (
        VectorizerFactory.text2vec_transformers(),
        {
            "text2vec-transformers": {
                "vectorizeClassName": True,
                "poolingStrategy": "masked_mean",
            }
        },
    ),
    (
        VectorizerFactory.text2vec_transformers(
            pooling_strategy="cls",
            vectorize_class_name=False,
        ),
        {
            "text2vec-transformers": {
                "vectorizeClassName": False,
                "poolingStrategy": "cls",
            }
        },
    ),
    (
        VectorizerFactory.img2vec_neural(
            image_fields=["test"],
        ),
        {
            "img2vec-neural": {
                "imageFields": ["test"],
            }
        },
    ),
    (
        VectorizerFactory.multi2vec_clip(
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
        VectorizerFactory.multi2vec_clip(
            image_fields=[Multi2VecField(name="image", weight=0.5)],
            text_fields=[Multi2VecField(name="text", weight=0.5)],
            vectorize_class_name=False,
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
        VectorizerFactory.multi2vec_bind(
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
        VectorizerFactory.multi2vec_bind(
            audio_fields=[Multi2VecField(name="audio", weight=0.5)],
            depth_fields=[Multi2VecField(name="depth", weight=0.5)],
            image_fields=[Multi2VecField(name="image", weight=0.5)],
            imu_fields=[Multi2VecField(name="imu", weight=0.5)],
            text_fields=[Multi2VecField(name="text", weight=0.5)],
            thermal_fields=[Multi2VecField(name="thermal", weight=0.5)],
            vectorize_class_name=False,
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
        VectorizerFactory.ref2vec_centroid(reference_properties=["prop"]),
        {"ref2vec-centroid": {"referenceProperties": ["prop"], "method": "mean"}},
    ),
]


@pytest.mark.parametrize("vectorizer_config,expected", TEST_CONFIG_WITH_MODULE_PARAMETERS)
def test_config_with_module(vectorizer_config: VectorizerConfig, expected: dict):
    config = CollectionConfigCreate(name="test", vectorizer_config=vectorizer_config)
    assert config.to_dict() == {
        **DEFAULTS,
        "vectorizer": vectorizer_config.vectorizer.value,
        "class": "Test",
        "moduleConfig": expected,
    }


TEST_CONFIG_WITH_MODULE_AND_PROPERTIES_PARAMETERS = [
    (
        VectorizerFactory.text2vec_transformers(),
        [
            Property(
                name="text",
                data_type=DataType.TEXT,
                vectorizer_config=PropertyVectorizerConfig(
                    skip=False, vectorize_property_name=False
                ),
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
                        "vectorizePropertyName": False,
                    }
                },
            }
        ],
    )
]


@pytest.mark.parametrize(
    "vectorizer_config,properties,expected_mc,expected_props",
    TEST_CONFIG_WITH_MODULE_AND_PROPERTIES_PARAMETERS,
)
def test_config_with_module_and_properties(
    vectorizer_config: VectorizerConfig,
    properties: List[Property],
    expected_mc: dict,
    expected_props: dict,
):
    config = CollectionConfigCreate(
        name="test", properties=properties, vectorizer_config=vectorizer_config
    )
    assert config.to_dict() == {
        **DEFAULTS,
        "vectorizer": vectorizer_config.vectorizer.value,
        "class": "Test",
        "properties": expected_props,
        "moduleConfig": expected_mc,
    }


def test_config_with_properties():
    config = CollectionConfigCreate(
        name="test",
        description="test",
        vectorizer_config=VectorizerConfig(vectorizer=Vectorizer.NONE),
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
    assert config.to_dict() == {
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
