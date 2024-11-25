from weaviate.proto.v1 import base_pb2 as _base_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class GenerativeSearch(_message.Message):
    __slots__ = (
        "single_response_prompt",
        "grouped_response_task",
        "grouped_properties",
        "single",
        "grouped",
    )

    class Single(_message.Message):
        __slots__ = ("prompt", "debug", "queries")
        PROMPT_FIELD_NUMBER: _ClassVar[int]
        DEBUG_FIELD_NUMBER: _ClassVar[int]
        QUERIES_FIELD_NUMBER: _ClassVar[int]
        prompt: str
        debug: bool
        queries: _containers.RepeatedCompositeFieldContainer[GenerativeProvider]
        def __init__(
            self,
            prompt: _Optional[str] = ...,
            debug: bool = ...,
            queries: _Optional[_Iterable[_Union[GenerativeProvider, _Mapping]]] = ...,
        ) -> None: ...

    class Grouped(_message.Message):
        __slots__ = ("task", "properties", "queries")
        TASK_FIELD_NUMBER: _ClassVar[int]
        PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        QUERIES_FIELD_NUMBER: _ClassVar[int]
        task: str
        properties: _base_pb2.TextArray
        queries: _containers.RepeatedCompositeFieldContainer[GenerativeProvider]
        def __init__(
            self,
            task: _Optional[str] = ...,
            properties: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
            queries: _Optional[_Iterable[_Union[GenerativeProvider, _Mapping]]] = ...,
        ) -> None: ...

    SINGLE_RESPONSE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    GROUPED_RESPONSE_TASK_FIELD_NUMBER: _ClassVar[int]
    GROUPED_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    SINGLE_FIELD_NUMBER: _ClassVar[int]
    GROUPED_FIELD_NUMBER: _ClassVar[int]
    single_response_prompt: str
    grouped_response_task: str
    grouped_properties: _containers.RepeatedScalarFieldContainer[str]
    single: GenerativeSearch.Single
    grouped: GenerativeSearch.Grouped
    def __init__(
        self,
        single_response_prompt: _Optional[str] = ...,
        grouped_response_task: _Optional[str] = ...,
        grouped_properties: _Optional[_Iterable[str]] = ...,
        single: _Optional[_Union[GenerativeSearch.Single, _Mapping]] = ...,
        grouped: _Optional[_Union[GenerativeSearch.Grouped, _Mapping]] = ...,
    ) -> None: ...

class GenerativeProvider(_message.Message):
    __slots__ = (
        "return_metadata",
        "anthropic",
        "anyscale",
        "aws",
        "cohere",
        "dummy",
        "mistral",
        "ollama",
        "openai",
        "google",
        "databricks",
        "friendliai",
    )
    RETURN_METADATA_FIELD_NUMBER: _ClassVar[int]
    ANTHROPIC_FIELD_NUMBER: _ClassVar[int]
    ANYSCALE_FIELD_NUMBER: _ClassVar[int]
    AWS_FIELD_NUMBER: _ClassVar[int]
    COHERE_FIELD_NUMBER: _ClassVar[int]
    DUMMY_FIELD_NUMBER: _ClassVar[int]
    MISTRAL_FIELD_NUMBER: _ClassVar[int]
    OLLAMA_FIELD_NUMBER: _ClassVar[int]
    OPENAI_FIELD_NUMBER: _ClassVar[int]
    GOOGLE_FIELD_NUMBER: _ClassVar[int]
    DATABRICKS_FIELD_NUMBER: _ClassVar[int]
    FRIENDLIAI_FIELD_NUMBER: _ClassVar[int]
    return_metadata: bool
    anthropic: GenerativeAnthropic
    anyscale: GenerativeAnyscale
    aws: GenerativeAWS
    cohere: GenerativeCohere
    dummy: GenerativeDummy
    mistral: GenerativeMistral
    ollama: GenerativeOllama
    openai: GenerativeOpenAI
    google: GenerativeGoogle
    databricks: GenerativeDatabricks
    friendliai: GenerativeFriendliAI
    def __init__(
        self,
        return_metadata: bool = ...,
        anthropic: _Optional[_Union[GenerativeAnthropic, _Mapping]] = ...,
        anyscale: _Optional[_Union[GenerativeAnyscale, _Mapping]] = ...,
        aws: _Optional[_Union[GenerativeAWS, _Mapping]] = ...,
        cohere: _Optional[_Union[GenerativeCohere, _Mapping]] = ...,
        dummy: _Optional[_Union[GenerativeDummy, _Mapping]] = ...,
        mistral: _Optional[_Union[GenerativeMistral, _Mapping]] = ...,
        ollama: _Optional[_Union[GenerativeOllama, _Mapping]] = ...,
        openai: _Optional[_Union[GenerativeOpenAI, _Mapping]] = ...,
        google: _Optional[_Union[GenerativeGoogle, _Mapping]] = ...,
        databricks: _Optional[_Union[GenerativeDatabricks, _Mapping]] = ...,
        friendliai: _Optional[_Union[GenerativeFriendliAI, _Mapping]] = ...,
    ) -> None: ...

class GenerativeAnthropic(_message.Message):
    __slots__ = (
        "base_url",
        "max_tokens",
        "model",
        "temperature",
        "top_k",
        "top_p",
        "stop_sequences",
    )
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    STOP_SEQUENCES_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    max_tokens: int
    model: str
    temperature: float
    top_k: int
    top_p: float
    stop_sequences: _base_pb2.TextArray
    def __init__(
        self,
        base_url: _Optional[str] = ...,
        max_tokens: _Optional[int] = ...,
        model: _Optional[str] = ...,
        temperature: _Optional[float] = ...,
        top_k: _Optional[int] = ...,
        top_p: _Optional[float] = ...,
        stop_sequences: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
    ) -> None: ...

class GenerativeAnyscale(_message.Message):
    __slots__ = ("base_url", "model", "temperature")
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    model: str
    temperature: float
    def __init__(
        self,
        base_url: _Optional[str] = ...,
        model: _Optional[str] = ...,
        temperature: _Optional[float] = ...,
    ) -> None: ...

class GenerativeAWS(_message.Message):
    __slots__ = (
        "model",
        "temperature",
        "service",
        "region",
        "endpoint",
        "target_model",
        "target_variant",
    )
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    TARGET_MODEL_FIELD_NUMBER: _ClassVar[int]
    TARGET_VARIANT_FIELD_NUMBER: _ClassVar[int]
    model: str
    temperature: float
    service: str
    region: str
    endpoint: str
    target_model: str
    target_variant: str
    def __init__(
        self,
        model: _Optional[str] = ...,
        temperature: _Optional[float] = ...,
        service: _Optional[str] = ...,
        region: _Optional[str] = ...,
        endpoint: _Optional[str] = ...,
        target_model: _Optional[str] = ...,
        target_variant: _Optional[str] = ...,
    ) -> None: ...

class GenerativeCohere(_message.Message):
    __slots__ = (
        "base_url",
        "frequency_penalty",
        "max_tokens",
        "model",
        "k",
        "p",
        "presence_penalty",
        "stop_sequences",
        "temperature",
    )
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    FREQUENCY_PENALTY_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    K_FIELD_NUMBER: _ClassVar[int]
    P_FIELD_NUMBER: _ClassVar[int]
    PRESENCE_PENALTY_FIELD_NUMBER: _ClassVar[int]
    STOP_SEQUENCES_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    frequency_penalty: float
    max_tokens: int
    model: str
    k: int
    p: float
    presence_penalty: float
    stop_sequences: _base_pb2.TextArray
    temperature: float
    def __init__(
        self,
        base_url: _Optional[str] = ...,
        frequency_penalty: _Optional[float] = ...,
        max_tokens: _Optional[int] = ...,
        model: _Optional[str] = ...,
        k: _Optional[int] = ...,
        p: _Optional[float] = ...,
        presence_penalty: _Optional[float] = ...,
        stop_sequences: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
        temperature: _Optional[float] = ...,
    ) -> None: ...

class GenerativeDummy(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GenerativeMistral(_message.Message):
    __slots__ = ("base_url", "max_tokens", "model", "temperature", "top_p")
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    max_tokens: int
    model: str
    temperature: float
    top_p: float
    def __init__(
        self,
        base_url: _Optional[str] = ...,
        max_tokens: _Optional[int] = ...,
        model: _Optional[str] = ...,
        temperature: _Optional[float] = ...,
        top_p: _Optional[float] = ...,
    ) -> None: ...

class GenerativeOllama(_message.Message):
    __slots__ = ("api_endpoint", "model", "temperature")
    API_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    api_endpoint: str
    model: str
    temperature: float
    def __init__(
        self,
        api_endpoint: _Optional[str] = ...,
        model: _Optional[str] = ...,
        temperature: _Optional[float] = ...,
    ) -> None: ...

class GenerativeOpenAI(_message.Message):
    __slots__ = (
        "frequency_penalty",
        "max_tokens",
        "model",
        "n",
        "presence_penalty",
        "stop",
        "temperature",
        "top_p",
        "base_url",
        "api_version",
        "resource_name",
        "deployment_id",
        "is_azure",
    )
    FREQUENCY_PENALTY_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    N_FIELD_NUMBER: _ClassVar[int]
    PRESENCE_PENALTY_FIELD_NUMBER: _ClassVar[int]
    STOP_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    API_VERSION_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_NAME_FIELD_NUMBER: _ClassVar[int]
    DEPLOYMENT_ID_FIELD_NUMBER: _ClassVar[int]
    IS_AZURE_FIELD_NUMBER: _ClassVar[int]
    frequency_penalty: float
    max_tokens: int
    model: str
    n: int
    presence_penalty: float
    stop: _base_pb2.TextArray
    temperature: float
    top_p: float
    base_url: str
    api_version: str
    resource_name: str
    deployment_id: str
    is_azure: bool
    def __init__(
        self,
        frequency_penalty: _Optional[float] = ...,
        max_tokens: _Optional[int] = ...,
        model: _Optional[str] = ...,
        n: _Optional[int] = ...,
        presence_penalty: _Optional[float] = ...,
        stop: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
        temperature: _Optional[float] = ...,
        top_p: _Optional[float] = ...,
        base_url: _Optional[str] = ...,
        api_version: _Optional[str] = ...,
        resource_name: _Optional[str] = ...,
        deployment_id: _Optional[str] = ...,
        is_azure: bool = ...,
    ) -> None: ...

class GenerativeGoogle(_message.Message):
    __slots__ = (
        "frequency_penalty",
        "max_tokens",
        "model",
        "presence_penalty",
        "temperature",
        "top_k",
        "top_p",
        "stop_sequences",
        "api_endpoint",
        "project_id",
        "endpoint_id",
        "region",
    )
    FREQUENCY_PENALTY_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    PRESENCE_PENALTY_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    STOP_SEQUENCES_FIELD_NUMBER: _ClassVar[int]
    API_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    ENDPOINT_ID_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    frequency_penalty: float
    max_tokens: int
    model: str
    presence_penalty: float
    temperature: float
    top_k: int
    top_p: float
    stop_sequences: _base_pb2.TextArray
    api_endpoint: str
    project_id: str
    endpoint_id: str
    region: str
    def __init__(
        self,
        frequency_penalty: _Optional[float] = ...,
        max_tokens: _Optional[int] = ...,
        model: _Optional[str] = ...,
        presence_penalty: _Optional[float] = ...,
        temperature: _Optional[float] = ...,
        top_k: _Optional[int] = ...,
        top_p: _Optional[float] = ...,
        stop_sequences: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
        api_endpoint: _Optional[str] = ...,
        project_id: _Optional[str] = ...,
        endpoint_id: _Optional[str] = ...,
        region: _Optional[str] = ...,
    ) -> None: ...

class GenerativeDatabricks(_message.Message):
    __slots__ = (
        "endpoint",
        "model",
        "frequency_penalty",
        "log_probs",
        "top_log_probs",
        "max_tokens",
        "n",
        "presence_penalty",
        "stop",
        "temperature",
        "top_p",
    )
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    FREQUENCY_PENALTY_FIELD_NUMBER: _ClassVar[int]
    LOG_PROBS_FIELD_NUMBER: _ClassVar[int]
    TOP_LOG_PROBS_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    N_FIELD_NUMBER: _ClassVar[int]
    PRESENCE_PENALTY_FIELD_NUMBER: _ClassVar[int]
    STOP_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    endpoint: str
    model: str
    frequency_penalty: float
    log_probs: bool
    top_log_probs: int
    max_tokens: int
    n: int
    presence_penalty: float
    stop: _base_pb2.TextArray
    temperature: float
    top_p: float
    def __init__(
        self,
        endpoint: _Optional[str] = ...,
        model: _Optional[str] = ...,
        frequency_penalty: _Optional[float] = ...,
        log_probs: bool = ...,
        top_log_probs: _Optional[int] = ...,
        max_tokens: _Optional[int] = ...,
        n: _Optional[int] = ...,
        presence_penalty: _Optional[float] = ...,
        stop: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
        temperature: _Optional[float] = ...,
        top_p: _Optional[float] = ...,
    ) -> None: ...

class GenerativeFriendliAI(_message.Message):
    __slots__ = ("base_url", "model", "max_tokens", "temperature", "n", "top_p")
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    N_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    model: str
    max_tokens: int
    temperature: float
    n: int
    top_p: float
    def __init__(
        self,
        base_url: _Optional[str] = ...,
        model: _Optional[str] = ...,
        max_tokens: _Optional[int] = ...,
        temperature: _Optional[float] = ...,
        n: _Optional[int] = ...,
        top_p: _Optional[float] = ...,
    ) -> None: ...

class GenerativeAnthropicMetadata(_message.Message):
    __slots__ = ("usage",)

    class Usage(_message.Message):
        __slots__ = ("input_tokens", "output_tokens")
        INPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        OUTPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        input_tokens: int
        output_tokens: int
        def __init__(
            self, input_tokens: _Optional[int] = ..., output_tokens: _Optional[int] = ...
        ) -> None: ...

    USAGE_FIELD_NUMBER: _ClassVar[int]
    usage: GenerativeAnthropicMetadata.Usage
    def __init__(
        self, usage: _Optional[_Union[GenerativeAnthropicMetadata.Usage, _Mapping]] = ...
    ) -> None: ...

class GenerativeAnyscaleMetadata(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GenerativeAWSMetadata(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GenerativeCohereMetadata(_message.Message):
    __slots__ = ("api_version", "billed_units", "tokens", "warnings")

    class ApiVersion(_message.Message):
        __slots__ = ("version", "is_deprecated", "is_experimental")
        VERSION_FIELD_NUMBER: _ClassVar[int]
        IS_DEPRECATED_FIELD_NUMBER: _ClassVar[int]
        IS_EXPERIMENTAL_FIELD_NUMBER: _ClassVar[int]
        version: str
        is_deprecated: bool
        is_experimental: bool
        def __init__(
            self,
            version: _Optional[str] = ...,
            is_deprecated: bool = ...,
            is_experimental: bool = ...,
        ) -> None: ...

    class BilledUnits(_message.Message):
        __slots__ = ("input_tokens", "output_tokens", "search_units", "classifications")
        INPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        OUTPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        SEARCH_UNITS_FIELD_NUMBER: _ClassVar[int]
        CLASSIFICATIONS_FIELD_NUMBER: _ClassVar[int]
        input_tokens: float
        output_tokens: float
        search_units: float
        classifications: float
        def __init__(
            self,
            input_tokens: _Optional[float] = ...,
            output_tokens: _Optional[float] = ...,
            search_units: _Optional[float] = ...,
            classifications: _Optional[float] = ...,
        ) -> None: ...

    class Tokens(_message.Message):
        __slots__ = ("input_tokens", "output_tokens")
        INPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        OUTPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        input_tokens: float
        output_tokens: float
        def __init__(
            self, input_tokens: _Optional[float] = ..., output_tokens: _Optional[float] = ...
        ) -> None: ...

    API_VERSION_FIELD_NUMBER: _ClassVar[int]
    BILLED_UNITS_FIELD_NUMBER: _ClassVar[int]
    TOKENS_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    api_version: GenerativeCohereMetadata.ApiVersion
    billed_units: GenerativeCohereMetadata.BilledUnits
    tokens: GenerativeCohereMetadata.Tokens
    warnings: _base_pb2.TextArray
    def __init__(
        self,
        api_version: _Optional[_Union[GenerativeCohereMetadata.ApiVersion, _Mapping]] = ...,
        billed_units: _Optional[_Union[GenerativeCohereMetadata.BilledUnits, _Mapping]] = ...,
        tokens: _Optional[_Union[GenerativeCohereMetadata.Tokens, _Mapping]] = ...,
        warnings: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
    ) -> None: ...

class GenerativeDummyMetadata(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GenerativeMistralMetadata(_message.Message):
    __slots__ = ("usage",)

    class Usage(_message.Message):
        __slots__ = ("prompt_tokens", "completion_tokens", "total_tokens")
        PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
        TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
        prompt_tokens: int
        completion_tokens: int
        total_tokens: int
        def __init__(
            self,
            prompt_tokens: _Optional[int] = ...,
            completion_tokens: _Optional[int] = ...,
            total_tokens: _Optional[int] = ...,
        ) -> None: ...

    USAGE_FIELD_NUMBER: _ClassVar[int]
    usage: GenerativeMistralMetadata.Usage
    def __init__(
        self, usage: _Optional[_Union[GenerativeMistralMetadata.Usage, _Mapping]] = ...
    ) -> None: ...

class GenerativeOllamaMetadata(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GenerativeOpenAIMetadata(_message.Message):
    __slots__ = ("usage",)

    class Usage(_message.Message):
        __slots__ = ("prompt_tokens", "completion_tokens", "total_tokens")
        PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
        TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
        prompt_tokens: int
        completion_tokens: int
        total_tokens: int
        def __init__(
            self,
            prompt_tokens: _Optional[int] = ...,
            completion_tokens: _Optional[int] = ...,
            total_tokens: _Optional[int] = ...,
        ) -> None: ...

    USAGE_FIELD_NUMBER: _ClassVar[int]
    usage: GenerativeOpenAIMetadata.Usage
    def __init__(
        self, usage: _Optional[_Union[GenerativeOpenAIMetadata.Usage, _Mapping]] = ...
    ) -> None: ...

class GenerativeGoogleMetadata(_message.Message):
    __slots__ = ("metadata", "usage_metadata")

    class TokenCount(_message.Message):
        __slots__ = ("total_billable_characters", "total_tokens")
        TOTAL_BILLABLE_CHARACTERS_FIELD_NUMBER: _ClassVar[int]
        TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
        total_billable_characters: int
        total_tokens: int
        def __init__(
            self,
            total_billable_characters: _Optional[int] = ...,
            total_tokens: _Optional[int] = ...,
        ) -> None: ...

    class TokenMetadata(_message.Message):
        __slots__ = ("input_token_count", "output_token_count")
        INPUT_TOKEN_COUNT_FIELD_NUMBER: _ClassVar[int]
        OUTPUT_TOKEN_COUNT_FIELD_NUMBER: _ClassVar[int]
        input_token_count: GenerativeGoogleMetadata.TokenCount
        output_token_count: GenerativeGoogleMetadata.TokenCount
        def __init__(
            self,
            input_token_count: _Optional[
                _Union[GenerativeGoogleMetadata.TokenCount, _Mapping]
            ] = ...,
            output_token_count: _Optional[
                _Union[GenerativeGoogleMetadata.TokenCount, _Mapping]
            ] = ...,
        ) -> None: ...

    class Metadata(_message.Message):
        __slots__ = ("token_metadata",)
        TOKEN_METADATA_FIELD_NUMBER: _ClassVar[int]
        token_metadata: GenerativeGoogleMetadata.TokenMetadata
        def __init__(
            self,
            token_metadata: _Optional[
                _Union[GenerativeGoogleMetadata.TokenMetadata, _Mapping]
            ] = ...,
        ) -> None: ...

    class UsageMetadata(_message.Message):
        __slots__ = ("prompt_token_count", "candidates_token_count", "total_token_count")
        PROMPT_TOKEN_COUNT_FIELD_NUMBER: _ClassVar[int]
        CANDIDATES_TOKEN_COUNT_FIELD_NUMBER: _ClassVar[int]
        TOTAL_TOKEN_COUNT_FIELD_NUMBER: _ClassVar[int]
        prompt_token_count: int
        candidates_token_count: int
        total_token_count: int
        def __init__(
            self,
            prompt_token_count: _Optional[int] = ...,
            candidates_token_count: _Optional[int] = ...,
            total_token_count: _Optional[int] = ...,
        ) -> None: ...

    METADATA_FIELD_NUMBER: _ClassVar[int]
    USAGE_METADATA_FIELD_NUMBER: _ClassVar[int]
    metadata: GenerativeGoogleMetadata.Metadata
    usage_metadata: GenerativeGoogleMetadata.UsageMetadata
    def __init__(
        self,
        metadata: _Optional[_Union[GenerativeGoogleMetadata.Metadata, _Mapping]] = ...,
        usage_metadata: _Optional[_Union[GenerativeGoogleMetadata.UsageMetadata, _Mapping]] = ...,
    ) -> None: ...

class GenerativeDatabricksMetadata(_message.Message):
    __slots__ = ("usage",)

    class Usage(_message.Message):
        __slots__ = ("prompt_tokens", "completion_tokens", "total_tokens")
        PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
        TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
        prompt_tokens: int
        completion_tokens: int
        total_tokens: int
        def __init__(
            self,
            prompt_tokens: _Optional[int] = ...,
            completion_tokens: _Optional[int] = ...,
            total_tokens: _Optional[int] = ...,
        ) -> None: ...

    USAGE_FIELD_NUMBER: _ClassVar[int]
    usage: GenerativeDatabricksMetadata.Usage
    def __init__(
        self, usage: _Optional[_Union[GenerativeDatabricksMetadata.Usage, _Mapping]] = ...
    ) -> None: ...

class GenerativeFriendliAIMetadata(_message.Message):
    __slots__ = ("usage",)

    class Usage(_message.Message):
        __slots__ = ("prompt_tokens", "completion_tokens", "total_tokens")
        PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
        COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
        TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
        prompt_tokens: int
        completion_tokens: int
        total_tokens: int
        def __init__(
            self,
            prompt_tokens: _Optional[int] = ...,
            completion_tokens: _Optional[int] = ...,
            total_tokens: _Optional[int] = ...,
        ) -> None: ...

    USAGE_FIELD_NUMBER: _ClassVar[int]
    usage: GenerativeFriendliAIMetadata.Usage
    def __init__(
        self, usage: _Optional[_Union[GenerativeFriendliAIMetadata.Usage, _Mapping]] = ...
    ) -> None: ...

class GenerativeMetadata(_message.Message):
    __slots__ = (
        "anthropic",
        "anyscale",
        "aws",
        "cohere",
        "dummy",
        "mistral",
        "ollama",
        "openai",
        "google",
        "databricks",
        "friendliai",
    )
    ANTHROPIC_FIELD_NUMBER: _ClassVar[int]
    ANYSCALE_FIELD_NUMBER: _ClassVar[int]
    AWS_FIELD_NUMBER: _ClassVar[int]
    COHERE_FIELD_NUMBER: _ClassVar[int]
    DUMMY_FIELD_NUMBER: _ClassVar[int]
    MISTRAL_FIELD_NUMBER: _ClassVar[int]
    OLLAMA_FIELD_NUMBER: _ClassVar[int]
    OPENAI_FIELD_NUMBER: _ClassVar[int]
    GOOGLE_FIELD_NUMBER: _ClassVar[int]
    DATABRICKS_FIELD_NUMBER: _ClassVar[int]
    FRIENDLIAI_FIELD_NUMBER: _ClassVar[int]
    anthropic: GenerativeAnthropicMetadata
    anyscale: GenerativeAnyscaleMetadata
    aws: GenerativeAWSMetadata
    cohere: GenerativeCohereMetadata
    dummy: GenerativeDummyMetadata
    mistral: GenerativeMistralMetadata
    ollama: GenerativeOllamaMetadata
    openai: GenerativeOpenAIMetadata
    google: GenerativeGoogleMetadata
    databricks: GenerativeDatabricksMetadata
    friendliai: GenerativeFriendliAIMetadata
    def __init__(
        self,
        anthropic: _Optional[_Union[GenerativeAnthropicMetadata, _Mapping]] = ...,
        anyscale: _Optional[_Union[GenerativeAnyscaleMetadata, _Mapping]] = ...,
        aws: _Optional[_Union[GenerativeAWSMetadata, _Mapping]] = ...,
        cohere: _Optional[_Union[GenerativeCohereMetadata, _Mapping]] = ...,
        dummy: _Optional[_Union[GenerativeDummyMetadata, _Mapping]] = ...,
        mistral: _Optional[_Union[GenerativeMistralMetadata, _Mapping]] = ...,
        ollama: _Optional[_Union[GenerativeOllamaMetadata, _Mapping]] = ...,
        openai: _Optional[_Union[GenerativeOpenAIMetadata, _Mapping]] = ...,
        google: _Optional[_Union[GenerativeGoogleMetadata, _Mapping]] = ...,
        databricks: _Optional[_Union[GenerativeDatabricksMetadata, _Mapping]] = ...,
        friendliai: _Optional[_Union[GenerativeFriendliAIMetadata, _Mapping]] = ...,
    ) -> None: ...

class GenerativeReply(_message.Message):
    __slots__ = ("result", "debug", "metadata")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    DEBUG_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    result: str
    debug: GenerativeDebug
    metadata: GenerativeMetadata
    def __init__(
        self,
        result: _Optional[str] = ...,
        debug: _Optional[_Union[GenerativeDebug, _Mapping]] = ...,
        metadata: _Optional[_Union[GenerativeMetadata, _Mapping]] = ...,
    ) -> None: ...

class GenerativeResult(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[GenerativeReply]
    def __init__(
        self, values: _Optional[_Iterable[_Union[GenerativeReply, _Mapping]]] = ...
    ) -> None: ...

class GenerativeDebug(_message.Message):
    __slots__ = ("full_prompt",)
    FULL_PROMPT_FIELD_NUMBER: _ClassVar[int]
    full_prompt: str
    def __init__(self, full_prompt: _Optional[str] = ...) -> None: ...
