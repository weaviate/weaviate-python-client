import pytest
from typing import List
from weaviate.collection.classes.config import (
    CollectionConfig,
    DataType,
    Img2VecNeuralConfig,
    ModuleConfig,
    Multi2VecClipConfig,
    Multi2VecClipConfigWeights,
    Multi2VecBindConfig,
    Multi2VecBindConfigWeights,
    Text2VecAzureOpenAIConfig,
    Text2VecCohereConfig,
    Text2VecGPT4AllConfig,
    Text2VecHuggingFaceConfig,
    Text2VecHuggingFaceConfigOptions,
    Text2VecOpenAIConfig,
    Text2VecPalmConfig,
    Text2VecTransformersConfig,
    Ref2VecCentroidConfig,
    Property,
    PropertyModuleConfig,
    Vectorizer,
)


DEFAULTS = {
    "vectorizer": "none",
    "vectorIndexType": "hnsw",
}


def test_basic_config():
    config = CollectionConfig(
        name="test",
        description="test",
    )
    assert config.to_dict() == {
        **DEFAULTS,
        "class": "Test",
        "description": "test",
    }


def test_config_with_vectorizer():
    config = CollectionConfig(
        name="test",
        description="test",
        vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
    )
    assert config.to_dict() == {
        **DEFAULTS,
        "class": "Test",
        "description": "test",
        "vectorizer": "text2vec-contextionary",
    }


TEST_CONFIG_WITH_MODULE_PARAMETERS = [
    (
        Vectorizer.TEXT2VEC_OPENAI,
        Text2VecAzureOpenAIConfig(
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
        Vectorizer.TEXT2VEC_COHERE,
        Text2VecCohereConfig(),
        {"text2vec-cohere": {"model": "embed_multilingual_v2.0", "truncate": "RIGHT"}},
    ),
    (
        Vectorizer.TEXT2VEC_COHERE,
        Text2VecCohereConfig(model="embed_multilingual_v2.0", truncate="NONE"),
        {"text2vec-cohere": {"model": "embed_multilingual_v2.0", "truncate": "NONE"}},
    ),
    (
        Vectorizer.TEXT2VEC_GPT4ALL,
        Text2VecGPT4AllConfig(),
        {
            "text2vec-gpt4all": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Vectorizer.TEXT2VEC_GPT4ALL,
        Text2VecGPT4AllConfig(
            vectorize_class_name=False,
        ),
        {
            "text2vec-gpt4all": {
                "vectorizeClassName": False,
            }
        },
    ),
    (
        Vectorizer.TEXT2VEC_HUGGINGFACE,
        Text2VecHuggingFaceConfig(
            model="model",
            options=Text2VecHuggingFaceConfigOptions(
                wait_for_model=False, use_gpu=False, use_cache=False
            ),
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
        Vectorizer.TEXT2VEC_HUGGINGFACE,
        Text2VecHuggingFaceConfig(
            passage_model="passageModel",
            query_model="queryModel",
            options=Text2VecHuggingFaceConfigOptions(
                wait_for_model=True, use_gpu=True, use_cache=True
            ),
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
        Vectorizer.TEXT2VEC_HUGGINGFACE,
        Text2VecHuggingFaceConfig(
            endpoint_url="endpoint",
        ),
        {
            "text2vec-huggingface": {
                "endpointURL": "endpoint",
            }
        },
    ),
    (
        Vectorizer.TEXT2VEC_OPENAI,
        Text2VecOpenAIConfig(),
        {
            "text2vec-openai": {
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Vectorizer.TEXT2VEC_OPENAI,
        Text2VecOpenAIConfig(
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
        Vectorizer.TEXT2VEC_PALM,
        Text2VecPalmConfig(
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
        Vectorizer.TEXT2VEC_PALM,
        Text2VecPalmConfig(
            project_id="project",
            api_endpoint="endpoint",
            model_id="model",
            vectorize_class_name=False,
        ),
        {
            "text2vec-palm": {
                "projectId": "project",
                "apiEndpoint": "endpoint",
                "modelId": "model",
                "vectorizeClassName": False,
            }
        },
    ),
    (
        Vectorizer.TEXT2VEC_TRANSFORMERS,
        Text2VecTransformersConfig(),
        {
            "text2vec-transformers": {
                "vectorizeClassName": True,
                "poolingStrategy": "masked_mean",
            }
        },
    ),
    (
        Vectorizer.TEXT2VEC_TRANSFORMERS,
        Text2VecTransformersConfig(
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
        Vectorizer.IMG2VEC_NEURAL,
        Img2VecNeuralConfig(
            image_fields=["test"],
        ),
        {
            "img2vec-neural": {
                "imageFields": ["test"],
            }
        },
    ),
    (
        Vectorizer.MULTI2VEC_CLIP,
        Multi2VecClipConfig(
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
        Vectorizer.MULTI2VEC_CLIP,
        Multi2VecClipConfig(
            image_fields=["image"],
            text_fields=["text"],
            vectorize_class_name=False,
            weights=Multi2VecClipConfigWeights(
                image_fields=[0.5],
                text_fields=[0.5],
            ),
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
        Vectorizer.MULTI2VEC_BIND,
        Multi2VecBindConfig(
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
        Vectorizer.MULTI2VEC_BIND,
        Multi2VecBindConfig(
            audio_fields=["audio"],
            depth_fields=["depth"],
            image_fields=["image"],
            imu_fields=["imu"],
            text_fields=["text"],
            thermal_fields=["thermal"],
            vectorize_class_name=False,
            weights=Multi2VecBindConfigWeights(
                audio_fields=[0.5],
                depth_fields=[0.5],
                image_fields=[0.5],
                imu_fields=[0.5],
                text_fields=[0.5],
                thermal_fields=[0.5],
            ),
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
        Vectorizer.REF2VEC_CENTROID,
        Ref2VecCentroidConfig(reference_properties=["prop"]),
        {"ref2vec-centroid": {"referenceProperties": ["prop"], "method": "mean"}},
    ),
]


@pytest.mark.parametrize("vectorizer,module_config,expected", TEST_CONFIG_WITH_MODULE_PARAMETERS)
def test_config_with_module(vectorizer: Vectorizer, module_config: ModuleConfig, expected: dict):
    config = CollectionConfig(name="test", vectorizer=vectorizer, module_config=module_config)
    assert config.to_dict() == {
        **DEFAULTS,
        "vectorizer": vectorizer.value,
        "class": "Test",
        "moduleConfig": expected,
    }


TEST_CONFIG_WITH_MODULE_AND_PROPERTIES_PARAMETERS = [
    (
        Vectorizer.TEXT2VEC_TRANSFORMERS,
        Text2VecTransformersConfig(),
        [
            Property(
                name="text",
                data_type=DataType.TEXT,
                module_config=PropertyModuleConfig(skip=False, vectorize_property_name=False),
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
    "vectorizer,module_config,properties,expected_mc,expected_props",
    TEST_CONFIG_WITH_MODULE_AND_PROPERTIES_PARAMETERS,
)
def test_config_with_module_and_properties(
    vectorizer: Vectorizer,
    module_config: ModuleConfig,
    properties: List[Property],
    expected_mc: dict,
    expected_props: dict,
):
    config = CollectionConfig(
        name="test", vectorizer=vectorizer, properties=properties, module_config=module_config
    )
    assert config.to_dict() == {
        **DEFAULTS,
        "vectorizer": vectorizer.value,
        "class": "Test",
        "properties": expected_props,
        "moduleConfig": expected_mc,
    }


def test_config_with_properties():
    config = CollectionConfig(
        name="test",
        description="test",
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
