from typing import List

import pytest
from pydantic import ValidationError

from weaviate.collections.classes.config import (
    _CollectionConfigCreate,
    DataType,
    _GenerativeProvider,
    _RerankerProvider,
    _VectorizerConfigCreate,
    Configure,
    Property,
    ReferenceProperty,
)
from weaviate.collections.classes.config_named_vectors import _NamedVectorConfigCreate
from weaviate.collections.classes.config_vectorizers import Multi2VecField, VectorDistances

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
            dimensions=356,
        ),
        {
            "text2vec-openai": {
                "resourceName": "resource",
                "deploymentId": "deployment",
                "vectorizeClassName": True,
                "baseURL": "https://api.openai.com/",
                "dimensions": 356,
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
        Configure.Vectorizer.multi2vec_cohere(
            model="embed-multilingual-v2.0",
            truncate="NONE",
            vectorize_collection_name=False,
            base_url="https://api.cohere.ai",
        ),
        {
            "multi2vec-cohere": {
                "model": "embed-multilingual-v2.0",
                "truncate": "NONE",
                "vectorizeClassName": False,
                "baseURL": "https://api.cohere.ai/",
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_voyageai(
            model="voyage-multimodal-3",
            truncation=False,
            output_encoding="base64",
            vectorize_collection_name=False,
            base_url="https://api.voyageai.com",
        ),
        {
            "multi2vec-voyageai": {
                "model": "voyage-multimodal-3",
                "truncation": False,
                "output_encoding": "base64",
                "vectorizeClassName": False,
                "baseURL": "https://api.voyageai.com/",
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_nvidia(
            model="nvidia/nvclip",
            truncation=False,
            output_encoding="base64",
            vectorize_collection_name=False,
            base_url="https://integrate.api.nvidia.com",
        ),
        {
            "multi2vec-nvidia": {
                "model": "nvidia/nvclip",
                "truncation": False,
                "output_encoding": "base64",
                "vectorizeClassName": False,
                "baseURL": "https://integrate.api.nvidia.com/",
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
                "service": "bedrock",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_aws(
            vectorize_collection_name=False,
            model="cohere.embed-english-v3",
            region="us-east-1",
            service="bedrock",
        ),
        {
            "text2vec-aws": {
                "vectorizeClassName": False,
                "model": "cohere.embed-english-v3",
                "region": "us-east-1",
                "service": "bedrock",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_aws(
            vectorize_collection_name=False,
            endpoint="something",
            region="us-east-1",
            service="sagemaker",
        ),
        {
            "text2vec-aws": {
                "vectorizeClassName": False,
                "endpoint": "something",
                "region": "us-east-1",
                "service": "sagemaker",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_databricks(
            vectorize_collection_name=False,
            endpoint="http://api.custom.com",
            instruction="instruction",
        ),
        {
            "text2vec-databricks": {
                "vectorizeClassName": False,
                "endpoint": "http://api.custom.com",
                "instruction": "instruction",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_ollama(
            vectorize_collection_name=False,
            model="cool-model",
            api_endpoint="https://123.0.0.4",
        ),
        {
            "text2vec-ollama": {
                "vectorizeClassName": False,
                "model": "cool-model",
                "apiEndpoint": "https://123.0.0.4",
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
            dimensions=100,
        ),
        {
            "text2vec-openai": {
                "vectorizeClassName": False,
                "model": "ada",
                "modelVersion": "002",
                "type": "text",
                "baseURL": "https://api.openai.com/",
                "dimensions": 100,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_mistral(
            vectorize_collection_name=False,
            model="cool-model",
        ),
        {
            "text2vec-mistral": {
                "vectorizeClassName": False,
                "model": "cool-model",
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
        Configure.Vectorizer.text2vec_google(
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
        Configure.Vectorizer.text2vec_google_aistudio(),
        {
            "text2vec-palm": {
                "apiEndpoint": "generativelanguage.googleapis.com",
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_palm(
            project_id="project",
            api_endpoint="api.google.com",
            model_id="model",
            vectorize_collection_name=False,
        ),
        {
            "text2vec-palm": {
                "projectId": "project",
                "apiEndpoint": "api.google.com",
                "modelId": "model",
                "vectorizeClassName": False,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_google(
            project_id="project",
            api_endpoint="api.google.com",
            model_id="model",
            vectorize_collection_name=False,
        ),
        {
            "text2vec-palm": {
                "projectId": "project",
                "apiEndpoint": "api.google.com",
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
            inference_url="https://api.transformers.com",
        ),
        {
            "text2vec-transformers": {
                "vectorizeClassName": False,
                "poolingStrategy": "cls",
                "inferenceUrl": "https://api.transformers.com",
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_jinaai(
            model="jina-embeddings-v3",
            vectorize_collection_name=False,
            dimensions=512,
        ),
        {
            "text2vec-jinaai": {
                "model": "jina-embeddings-v3",
                "vectorizeClassName": False,
                "dimensions": 512,
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_jinaai(
            model="jina-clip-v2",
            dimensions=512,
            vectorize_collection_name=False,
        ),
        {
            "multi2vec-jinaai": {
                "model": "jina-clip-v2",
                "dimensions": 512,
                "vectorizeClassName": False,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_voyageai(
            vectorize_collection_name=False,
            model="voyage-large-2",
            truncate=False,
            base_url="https://voyage.made-up.com",
        ),
        {
            "text2vec-voyageai": {
                "vectorizeClassName": False,
                "model": "voyage-large-2",
                "baseURL": "https://voyage.made-up.com",
                "truncate": False,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_nvidia(
            vectorize_collection_name=False,
            model="nvidia/nv-embed-v1",
            truncate=False,
            base_url="https://integrate.api.nvidia.com",
        ),
        {
            "text2vec-nvidia": {
                "vectorizeClassName": False,
                "model": "nvidia/nv-embed-v1",
                "baseURL": "https://integrate.api.nvidia.com",
                "truncate": False,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_weaviate(
            vectorize_collection_name=False,
            model="Snowflake/snowflake-arctic-embed-l-v2.0",
            base_url="https://api.embedding.weaviate.io",
            dimensions=1024,
        ),
        {
            "text2vec-weaviate": {
                "vectorizeClassName": False,
                "model": "Snowflake/snowflake-arctic-embed-l-v2.0",
                "baseURL": "https://api.embedding.weaviate.io",
                "dimensions": 1024,
            }
        },
    ),
    (
        Configure.Vectorizer.text2vec_weaviate(
            vectorize_collection_name=False,
            model="Snowflake/snowflake-arctic-embed-m-v1.5",
            base_url="https://api.embedding.weaviate.io",
            dimensions=768,
        ),
        {
            "text2vec-weaviate": {
                "vectorizeClassName": False,
                "model": "Snowflake/snowflake-arctic-embed-m-v1.5",
                "baseURL": "https://api.embedding.weaviate.io",
                "dimensions": 768,
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
        Configure.Vectorizer.multi2vec_palm(
            image_fields=["image"],
            text_fields=["text"],
            video_fields=["video"],
            project_id="project",
            video_interval_seconds=1,
            location="us-central1",
        ),
        {
            "multi2vec-palm": {
                "imageFields": ["image"],
                "textFields": ["text"],
                "videoFields": ["video"],
                "projectId": "project",
                "location": "us-central1",
                "videoIntervalSeconds": 1,
                "vectorizeClassName": True,
            }
        },
    ),
    (
        Configure.Vectorizer.multi2vec_google(
            image_fields=["image"],
            text_fields=["text"],
            video_fields=["video"],
            project_id="project",
            video_interval_seconds=1,
            location="us-central1",
        ),
        {
            "multi2vec-palm": {
                "imageFields": ["image"],
                "textFields": ["text"],
                "videoFields": ["video"],
                "projectId": "project",
                "location": "us-central1",
                "videoIntervalSeconds": 1,
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
def test_config_with_default_vectorizer(
    vectorizer_config: _VectorizerConfigCreate, expected: dict
) -> None:
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
        Configure.Generative.nvidia(),
        {"generative-nvidia": {}},
    ),
    (
        Configure.Generative.anyscale(),
        {"generative-anyscale": {}},
    ),
    (
        Configure.Generative.friendliai(
            temperature=0.5, max_tokens=100, model="model", base_url="https://api.custom.ai"
        ),
        {
            "generative-friendliai": {
                "temperature": 0.5,
                "maxTokens": 100,
                "model": "model",
                "baseURL": "https://api.custom.ai",
            }
        },
    ),
    (
        Configure.Generative.mistral(temperature=0.5, max_tokens=100, model="model"),
        {"generative-mistral": {"temperature": 0.5, "maxTokens": 100, "model": "model"}},
    ),
    (
        Configure.Generative.ollama(
            model="cool-model",
            api_endpoint="https://123.456.789.0",
        ),
        {
            "generative-ollama": {
                "model": "cool-model",
                "apiEndpoint": "https://123.456.789.0",
            }
        },
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
        Configure.Generative.google(project_id="project"),
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
                "apiEndpoint": "https://api.google.com",
                "maxOutputTokens": 100,
                "modelId": "model",
                "temperature": 0.5,
                "topK": 10,
                "topP": 0.5,
            }
        },
    ),
    (
        Configure.Generative.google(
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
                "apiEndpoint": "https://api.google.com",
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
                "service": "bedrock",
            }
        },
    ),
    (
        Configure.Generative.azure_openai(resource_name="name", deployment_id="id"),
        {
            "generative-openai": {
                "deploymentId": "id",
                "resourceName": "name",
            }
        },
    ),
    (
        Configure.Generative.azure_openai(
            resource_name="name",
            deployment_id="id",
            frequency_penalty=0.5,
            max_tokens=100,
            presence_penalty=0.5,
            temperature=0.5,
            top_p=0.5,
            base_url="https://api.openai.com",
        ),
        {
            "generative-openai": {
                "deploymentId": "id",
                "resourceName": "name",
                "frequencyPenaltyProperty": 0.5,
                "maxTokensProperty": 100,
                "presencePenaltyProperty": 0.5,
                "temperatureProperty": 0.5,
                "topPProperty": 0.5,
                "baseURL": "https://api.openai.com/",
            }
        },
    ),
    (
        Configure.Generative.anthropic(
            model="model",
            max_tokens=100,
            stop_sequences=["stop"],
            temperature=0.5,
            top_k=10,
            top_p=0.5,
        ),
        {
            "generative-anthropic": {
                "model": "model",
                "maxTokens": 100,
                "stopSequences": ["stop"],
                "temperature": 0.5,
                "topK": 10,
                "topP": 0.5,
            }
        },
    ),
    (
        Configure.Generative.databricks(endpoint="https://api.databricks.com"),
        {
            "generative-databricks": {
                "endpoint": "https://api.databricks.com",
            }
        },
    ),
    (
        Configure.Generative.databricks(
            endpoint="https://api.databricks.com",
            max_tokens=100,
            temperature=0.5,
            top_k=10,
            top_p=0.5,
        ),
        {
            "generative-databricks": {
                "endpoint": "https://api.databricks.com",
                "maxTokens": 100,
                "temperature": 0.5,
                "topK": 10,
                "topP": 0.5,
            }
        },
    ),
]


@pytest.mark.parametrize(
    "generative_config,expected_mc",
    TEST_CONFIG_WITH_GENERATIVE,
)
def test_config_with_generative(
    generative_config: _GenerativeProvider,
    expected_mc: dict,
) -> None:
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
        Configure.Reranker.voyageai(),
        {
            "reranker-voyageai": {},
        },
    ),
    (
        Configure.Reranker.voyageai(model="rerank-lite-1"),
        {
            "reranker-voyageai": {"model": "rerank-lite-1"},
        },
    ),
    (
        Configure.Reranker.jinaai(),
        {
            "reranker-jinaai": {},
        },
    ),
    (
        Configure.Reranker.jinaai(model="jina-reranker-v2-base-multilingual"),
        {
            "reranker-jinaai": {"model": "jina-reranker-v2-base-multilingual"},
        },
    ),
    (
        Configure.Reranker.nvidia(),
        {
            "reranker-nvidia": {},
        },
    ),
    (
        Configure.Reranker.nvidia(
            model="nvidia/llama-3.2-nv-rerankqa-1b-v2",
            base_url="https://integrate.api.nvidia.com/v1",
        ),
        {
            "reranker-nvidia": {
                "model": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
                "baseURL": "https://integrate.api.nvidia.com/v1",
            },
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
    reranker_config: _RerankerProvider,
    expected_mc: dict,
) -> None:
    config = _CollectionConfigCreate(name="test", reranker_config=reranker_config)
    assert config._to_dict() == {
        **DEFAULTS,
        "vectorizer": "none",
        "class": "Test",
        "moduleConfig": expected_mc,
    }


def test_config_with_properties() -> None:
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
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["text[]"],
                "name": "text_array",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["int"],
                "name": "int",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["int[]"],
                "name": "int_array",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["number"],
                "name": "number",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["number[]"],
                "name": "number_array",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["boolean"],
                "name": "bool",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["boolean[]"],
                "name": "bool_array",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["date"],
                "name": "date",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["date[]"],
                "name": "date_array",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["uuid"],
                "name": "uuid",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["uuid[]"],
                "name": "uuid_array",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["geoCoordinates"],
                "name": "geo",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["blob"],
                "name": "blob",
                "skip_vectorization": False,
                "vectorize_property_name": True,
            },
            {
                "dataType": ["phoneNumber"],
                "name": "phone_number",
                "skip_vectorization": False,
                "vectorize_property_name": True,
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


def test_vector_config_hnsw_sq() -> None:
    vector_index = Configure.VectorIndex.hnsw(
        ef_construction=128,
        quantizer=Configure.VectorIndex.Quantizer.sq(rescore_limit=123, training_limit=5012),
    )

    vi_dict = vector_index._to_dict()

    assert vi_dict["efConstruction"] == 128
    assert vi_dict["sq"]["rescoreLimit"] == 123
    assert vi_dict["sq"]["trainingLimit"] == 5012


def test_vector_config_flat_pq() -> None:
    vector_index = Configure.VectorIndex.flat(
        distance_metric=VectorDistances.DOT,
        vector_cache_max_objects=456,
        quantizer=Configure.VectorIndex.Quantizer.pq(segments=789),
    )

    vi_dict = vector_index._to_dict()

    assert vi_dict["distance"] == "dot"
    assert vi_dict["vectorCacheMaxObjects"] == 456
    assert "bitCompression" not in vi_dict["pq"]
    assert vi_dict["pq"]["segments"] == 789


TEST_CONFIG_WITH_NAMED_VECTORIZER_PARAMETERS = [
    (
        [Configure.NamedVectors.text2vec_contextionary(name="test", source_properties=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "text2vec-contextionary": {
                        "vectorizeClassName": True,
                        "properties": ["prop"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_azure_openai(
                name="test",
                resource_name="resource",
                deployment_id="deployment",
                source_properties=["prop"],
                dimensions=512,
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-openai": {
                        "resourceName": "resource",
                        "deploymentId": "deployment",
                        "vectorizeClassName": True,
                        "properties": ["prop"],
                        "dimensions": 512,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [Configure.NamedVectors.text2vec_cohere(name="test", source_properties=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "text2vec-cohere": {
                        "vectorizeClassName": True,
                        "properties": ["prop"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [Configure.NamedVectors.multi2vec_cohere(name="test", text_fields=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "multi2vec-cohere": {
                        "vectorizeClassName": True,
                        "textFields": ["prop"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [Configure.NamedVectors.multi2vec_voyageai(name="test", text_fields=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "multi2vec-voyageai": {
                        "vectorizeClassName": True,
                        "textFields": ["prop"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [Configure.NamedVectors.multi2vec_nvidia(name="test", text_fields=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "multi2vec-nvidia": {
                        "vectorizeClassName": True,
                        "textFields": ["prop"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.multi2vec_jinaai(
                name="test", dimensions=256, text_fields=["prop"]
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "multi2vec-jinaai": {
                        "dimensions": 256,
                        "vectorizeClassName": True,
                        "textFields": ["prop"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [Configure.NamedVectors.text2vec_gpt4all(name="test", source_properties=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "text2vec-gpt4all": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            },
        },
    ),
    (
        [Configure.NamedVectors.text2vec_huggingface(name="test", source_properties=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "text2vec-huggingface": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_aws(
                name="test", region="us-east-1", source_properties=["prop"]
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-aws": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                        "region": "us-east-1",
                        "service": "bedrock",
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_databricks(
                name="test", endpoint="http://api.custom.com", instruction="instruction"
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-databricks": {
                        "vectorizeClassName": True,
                        "instruction": "instruction",
                        "endpoint": "http://api.custom.com",
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_ollama(
                name="test",
                source_properties=["prop"],
                api_endpoint="https://123.0.0.4",
                model="cool-model",
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-ollama": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                        "apiEndpoint": "https://123.0.0.4",
                        "model": "cool-model",
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_openai(
                name="test", source_properties=["prop"], base_url="https://api.openai.com/"
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-openai": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                        "baseURL": "https://api.openai.com/",
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [Configure.NamedVectors.text2vec_mistral(name="test", source_properties=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "text2vec-mistral": {
                        "vectorizeClassName": True,
                        "properties": ["prop"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_palm(
                name="test",
                project_id="project",
                source_properties=["prop"],
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-palm": {
                        "projectId": "project",
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_google(
                name="test",
                project_id="project",
                source_properties=["prop"],
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-palm": {
                        "projectId": "project",
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_google_aistudio(
                name="test",
                source_properties=["prop"],
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-palm": {
                        "apiEndpoint": "generativelanguage.googleapis.com",
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [Configure.NamedVectors.text2vec_transformers(name="test", source_properties=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "text2vec-transformers": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                        "poolingStrategy": "masked_mean",
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_voyageai(
                name="test", source_properties=["prop"], truncate=True
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-voyageai": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                        "truncate": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_nvidia(
                name="test", source_properties=["prop"], truncate=True
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-nvidia": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                        "truncate": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.text2vec_weaviate(
                name="test",
                source_properties=["prop"],
                base_url="https://api.embedding.weaviate.io",
                dimensions=768,
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "text2vec-weaviate": {
                        "properties": ["prop"],
                        "vectorizeClassName": True,
                        "baseURL": "https://api.embedding.weaviate.io",
                        "dimensions": 768,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.img2vec_neural(
                name="test",
                image_fields=["test"],
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "img2vec-neural": {
                        "imageFields": ["test"],
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.multi2vec_clip(
                name="test",
                image_fields=["image"],
                text_fields=["text"],
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "multi2vec-clip": {
                        "imageFields": ["image"],
                        "textFields": ["text"],
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.multi2vec_palm(
                name="test",
                image_fields=["image"],
                text_fields=["text"],
                project_id="project",
                location="us-central1",
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "multi2vec-palm": {
                        "imageFields": ["image"],
                        "textFields": ["text"],
                        "projectId": "project",
                        "location": "us-central1",
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.multi2vec_google(
                name="test",
                image_fields=["image"],
                text_fields=["text"],
                project_id="project",
                location="us-central1",
            )
        ],
        {
            "test": {
                "vectorizer": {
                    "multi2vec-palm": {
                        "imageFields": ["image"],
                        "textFields": ["text"],
                        "projectId": "project",
                        "location": "us-central1",
                        "vectorizeClassName": True,
                    }
                },
                "vectorIndexType": "hnsw",
            }
        },
    ),
    (
        [
            Configure.NamedVectors.multi2vec_bind(
                name="test",
                audio_fields=["audio"],
                depth_fields=["depth"],
                image_fields=["image"],
                imu_fields=["imu"],
                text_fields=["text"],
                thermal_fields=["thermal"],
            )
        ],
        {
            "test": {
                "vectorizer": {
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
                "vectorIndexType": "hnsw",
            },
        },
    ),
    (
        [Configure.NamedVectors.ref2vec_centroid(name="test", reference_properties=["prop"])],
        {
            "test": {
                "vectorizer": {
                    "ref2vec-centroid": {"referenceProperties": ["prop"], "method": "mean"},
                },
                "vectorIndexType": "hnsw",
            },
        },
    ),
]


@pytest.mark.parametrize("vectorizer_config,expected", TEST_CONFIG_WITH_NAMED_VECTORIZER_PARAMETERS)
def test_config_with_named_vectors(
    vectorizer_config: List[_NamedVectorConfigCreate], expected: dict
) -> None:
    config = _CollectionConfigCreate(name="test", vectorizer_config=vectorizer_config)
    assert config._to_dict() == {
        "class": "Test",
        "vectorConfig": expected,
    }
