from collections.abc import Iterable
from dataclasses import dataclass
from io import BufferedReader
from pathlib import Path
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, Field, TypeAdapter
from typing_extensions import deprecated as typing_deprecated

from weaviate.collections.classes.config import (
    AWSService,
    GenerativeSearches,
    OpenAiReasoningEffort,
    OpenAiVerbosity,
    _EnumLikeStr,
)
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import base_pb2, generative_pb2
from weaviate.types import BLOB_INPUT
from weaviate.util import parse_blob


def _parse_anyhttpurl(url: Optional[AnyHttpUrl]) -> Optional[str]:
    if url is None:
        return None
    return str(url).strip("/")


def _to_text_array(values: Optional[Iterable[str]]) -> Optional[base_pb2.TextArray]:
    return base_pb2.TextArray(values=values) if values is not None else None


@dataclass
class _GenerativeConfigRuntimeOptions:
    return_metadata: bool = False
    images: Optional[Iterable[str]] = None
    image_properties: Optional[List[str]] = None


class _GenerativeConfigRuntime(BaseModel):
    generative: Union[GenerativeSearches, _EnumLikeStr]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        raise NotImplementedError("This method must be implemented in the child class")

    def _validate_multi_modal(self, opts: _GenerativeConfigRuntimeOptions) -> None:
        if opts.images is not None or opts.image_properties is not None:
            raise WeaviateInvalidInputError(
                f"The {self.generative.value} module does not support the `images` or `image_properties` options."
            )


GenerativeConfigRuntime = _GenerativeConfigRuntime


class _GenerativeAnthropic(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.ANTHROPIC, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    temperature: Optional[float]
    top_k: Optional[int]
    top_p: Optional[float]
    stop_sequences: Optional[List[str]]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            anthropic=generative_pb2.GenerativeAnthropic(
                base_url=_parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
                stop_sequences=_to_text_array(self.stop_sequences),
                images=_to_text_array(opts.images),
                image_properties=_to_text_array(opts.image_properties),
            ),
        )


class _GenerativeAnyscale(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.ANYSCALE, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    model: Optional[str]
    temperature: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            anyscale=generative_pb2.GenerativeAnyscale(
                base_url=_parse_anyhttpurl(self.base_url),
                model=self.model,
                temperature=self.temperature,
            ),
        )


class _GenerativeAWS(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.AWS, frozen=True, exclude=True
    )
    max_tokens: Optional[int]
    model: Optional[str]
    region: Optional[str]
    endpoint: Optional[AnyHttpUrl]
    service: Optional[str]
    target_model: Optional[str]
    target_variant: Optional[str]
    temperature: Optional[float]
    top_k: Optional[int]
    top_p: Optional[float]
    stop_sequences: Optional[List[str]]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            aws=generative_pb2.GenerativeAWS(
                model=self.model,
                region=self.region,
                endpoint=_parse_anyhttpurl(self.endpoint),
                service=self.service,
                target_model=self.target_model,
                target_variant=self.target_variant,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                images=_to_text_array(opts.images),
                image_properties=_to_text_array(opts.image_properties),
                # TODO - add top_k, top_p & stop_sequences here when added to server-side proto
                # Check the latest availble version of `grpc/proto/v1/generative.proto` (see GenerativeAWS) in the server repo
            ),
        )


class _GenerativeCohere(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.COHERE, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    k: Optional[int]
    max_tokens: Optional[int]
    model: Optional[str]
    p: Optional[float]
    presence_penalty: Optional[float]
    stop_sequences: Optional[List[str]]
    temperature: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            cohere=generative_pb2.GenerativeCohere(
                base_url=_parse_anyhttpurl(self.base_url),
                k=self.k,
                max_tokens=self.max_tokens,
                model=self.model,
                p=self.p,
                presence_penalty=self.presence_penalty,
                stop_sequences=_to_text_array(self.stop_sequences),
                temperature=self.temperature,
            ),
        )


class _GenerativeDatabricks(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.DATABRICKS, frozen=True, exclude=True
    )
    endpoint: AnyHttpUrl
    frequency_penalty: Optional[float]
    log_probs: Optional[bool]
    max_tokens: Optional[int]
    model: Optional[str]
    n: Optional[int]
    presence_penalty: Optional[float]
    stop: Optional[List[str]]
    temperature: Optional[float]
    top_log_probs: Optional[int]
    top_p: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            databricks=generative_pb2.GenerativeDatabricks(
                endpoint=_parse_anyhttpurl(self.endpoint),
                frequency_penalty=self.frequency_penalty,
                log_probs=self.log_probs or False,
                max_tokens=self.max_tokens,
                model=self.model,
                n=self.n,
                presence_penalty=self.presence_penalty,
                stop=_to_text_array(self.stop),
                temperature=self.temperature,
                top_log_probs=self.top_log_probs,
                top_p=self.top_p,
            ),
        )


class _GenerativeDummy(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.DUMMY, frozen=True, exclude=True
    )

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata, dummy=generative_pb2.GenerativeDummy()
        )


class _GenerativeFriendliai(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.FRIENDLIAI, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    n: Optional[int]
    temperature: Optional[float]
    top_p: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            friendliai=generative_pb2.GenerativeFriendliAI(
                base_url=_parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                n=self.n,
                temperature=self.temperature,
                top_p=self.top_p,
            ),
        )


class _GenerativeMistral(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.MISTRAL, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            mistral=generative_pb2.GenerativeMistral(
                base_url=_parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
            ),
        )


class _GenerativeNvidia(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.NVIDIA, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            nvidia=generative_pb2.GenerativeNvidia(
                base_url=_parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
            ),
        )


class _GenerativeOllama(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.OLLAMA, frozen=True, exclude=True
    )
    api_endpoint: Optional[AnyHttpUrl]
    model: Optional[str]
    temperature: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            ollama=generative_pb2.GenerativeOllama(
                api_endpoint=_parse_anyhttpurl(self.api_endpoint),
                model=self.model,
                temperature=self.temperature,
                images=_to_text_array(opts.images),
                image_properties=_to_text_array(opts.image_properties),
            ),
        )


class _GenerativeOpenAI(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.OPENAI, frozen=True, exclude=True
    )
    api_version: Optional[str]
    base_url: Optional[AnyHttpUrl]
    deployment_id: Optional[str]
    frequency_penalty: Optional[float]
    is_azure: bool
    max_tokens: Optional[int]
    model: Optional[str]
    presence_penalty: Optional[float]
    resource_name: Optional[str]
    stop: Optional[List[str]]
    temperature: Optional[float]
    top_p: Optional[float]
    verbosity: Optional[Union[OpenAiVerbosity, str]]
    reasoning_effort: Optional[Union[OpenAiReasoningEffort, str]]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            openai=generative_pb2.GenerativeOpenAI(
                api_version=self.api_version,
                base_url=_parse_anyhttpurl(self.base_url),
                deployment_id=self.deployment_id,
                frequency_penalty=self.frequency_penalty,
                max_tokens=self.max_tokens,
                model=self.model,
                presence_penalty=self.presence_penalty,
                resource_name=self.resource_name,
                stop=_to_text_array(self.stop),
                temperature=self.temperature,
                top_p=self.top_p,
                is_azure=self.is_azure,
                images=_to_text_array(opts.images),
                image_properties=_to_text_array(opts.image_properties),
                verbosity=self.__verbosity(),
                reasoning_effort=self.__reasoning_effort(),
            ),
        )

    def __verbosity(self):
        if self.verbosity is None:
            return None

        if self.verbosity == "low":
            return generative_pb2.GenerativeOpenAI.Verbosity.VERBOSITY_LOW
        if self.verbosity == "medium":
            return generative_pb2.GenerativeOpenAI.Verbosity.VERBOSITY_MEDIUM
        if self.verbosity == "high":
            return generative_pb2.GenerativeOpenAI.Verbosity.VERBOSITY_HIGH
        raise WeaviateInvalidInputError(f"Invalid verbosity value: {self.verbosity}")

    def __reasoning_effort(self):
        if self.reasoning_effort is None:
            return None

        if self.reasoning_effort == "minimal":
            return generative_pb2.GenerativeOpenAI.ReasoningEffort.REASONING_EFFORT_MINIMAL
        if self.reasoning_effort == "low":
            return generative_pb2.GenerativeOpenAI.ReasoningEffort.REASONING_EFFORT_LOW
        if self.reasoning_effort == "medium":
            return generative_pb2.GenerativeOpenAI.ReasoningEffort.REASONING_EFFORT_MEDIUM
        if self.reasoning_effort == "high":
            return generative_pb2.GenerativeOpenAI.ReasoningEffort.REASONING_EFFORT_HIGH
        raise WeaviateInvalidInputError(f"Invalid reasoning_effort value: {self.reasoning_effort}")


class _GenerativeGoogle(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.PALM, frozen=True, exclude=True
    )
    api_endpoint: Optional[AnyHttpUrl]
    endpoint_id: Optional[str]
    frequency_penalty: Optional[float]
    max_tokens: Optional[int]
    model: Optional[str]
    presence_penalty: Optional[float]
    project_id: Optional[str]
    region: Optional[str]
    stop_sequences: Optional[List[str]]
    temperature: Optional[float]
    top_k: Optional[int]
    top_p: Optional[float]

    def _parse_api_endpoint(self, url: Optional[AnyHttpUrl]) -> Optional[str]:
        return (
            u.replace("https://", "").replace("http://", "")
            if (u := _parse_anyhttpurl(url)) is not None
            else None
        )

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            google=generative_pb2.GenerativeGoogle(
                api_endpoint=self._parse_api_endpoint(self.api_endpoint),
                endpoint_id=self.endpoint_id,
                frequency_penalty=self.frequency_penalty,
                max_tokens=self.max_tokens,
                model=self.model,
                presence_penalty=self.presence_penalty,
                project_id=self.project_id,
                region=self.region,
                stop_sequences=_to_text_array(self.stop_sequences),
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
                images=_to_text_array(opts.images),
                image_properties=_to_text_array(opts.image_properties),
            ),
        )


class _GenerativeXAI(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.XAI, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            xai=generative_pb2.GenerativeXAI(
                base_url=_parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
                images=_to_text_array(opts.images),
                image_properties=_to_text_array(opts.image_properties),
            ),
        )


class _GenerativeContextualAI(_GenerativeConfigRuntime):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.CONTEXTUALAI, frozen=True, exclude=True
    )
    model: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]
    max_new_tokens: Optional[int]
    system_prompt: Optional[str]
    avoid_commentary: Optional[bool]
    knowledge: Optional[List[str]]

    def _to_grpc(self, opts: _GenerativeConfigRuntimeOptions) -> generative_pb2.GenerativeProvider:
        self._validate_multi_modal(opts)
        return generative_pb2.GenerativeProvider(
            return_metadata=opts.return_metadata,
            contextualai=generative_pb2.GenerativeContextualAI(
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
                max_new_tokens=self.max_new_tokens,
                system_prompt=self.system_prompt,
                avoid_commentary=self.avoid_commentary or False,
                knowledge=_to_text_array(self.knowledge),
            ),
        )


class GenerativeConfig:
    """Use this factory class to create the correct object for the `generative_provider` argument in the search methods of the `.generate` namespace.

    Each staticmethod provides options specific to the named generative search module in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications will be caught before the request is sent to Weaviate.
    """

    @staticmethod
    def anthropic(
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeAnthropic` object for use when performing dynamic AI generation using the `generative-anthropic` module.

        Args:
            base_url: The base URL to send the API request to. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            stop_sequences: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_k: The top K to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeAnthropic(
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            model=model,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

    @staticmethod
    def anyscale(
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeAnyscale` object for use when performing dynamic AI generation using the `generative-anyscale` module.

        Args:
            base_url: The base URL to send the API request to. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeAnyscale(
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            model=model,
            temperature=temperature,
        )

    @staticmethod
    @typing_deprecated(
        "`aws` is deprecated and will be removed after Q3 '26. Use a service-specific method instead, such as `aws_bedrock`."
    )
    def aws(
        *,
        endpoint: Optional[str] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        region: Optional[str] = None,
        service: Optional[Union[AWSService, str]] = None,
        target_model: Optional[str] = None,
        target_variant: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeAWS` object for use when performing dynamic AI generation using the `generative-aws` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-aws)
        for detailed usage.

        Args:
            endpoint: The endpoint to use when requesting the generation. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            region: The AWS region to run the model from. Defaults to `None`, which uses the server-defined default
            service: The AWS service to use. Defaults to `None`, which uses the server-defined default
            target_model: The target model to use. Defaults to `None`, which uses the server-defined default
            target_variant: The target variant to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeAWS(
            model=model,
            max_tokens=max_tokens,
            region=region,
            service=service,
            endpoint=TypeAdapter(AnyHttpUrl).validate_python(endpoint)
            if endpoint is not None
            else None,
            target_model=target_model,
            target_variant=target_variant,
            temperature=temperature,
            top_k=None,
            top_p=None,
            stop_sequences=None,
        )

    @staticmethod
    def aws_bedrock(
        *,
        endpoint: Optional[str] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        region: Optional[str] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeAWS` object for use when performing dynamic AI generation using the `generative-aws` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-aws)
        for detailed usage.

        Args:
            endpoint: The endpoint to use when requesting the generation. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            region: The AWS region to run the model from. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_k: The top K to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
            stop_sequences: The stop sequences to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeAWS(
            model=model,
            max_tokens=max_tokens,
            region=region,
            service="bedrock",
            endpoint=TypeAdapter(AnyHttpUrl).validate_python(endpoint)
            if endpoint is not None
            else None,
            target_model=None,
            target_variant=None,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            stop_sequences=stop_sequences,
        )

    @staticmethod
    def aws_sagemaker(
        *,
        endpoint: Optional[str] = None,
        max_tokens: Optional[int] = None,
        region: Optional[str] = None,
        target_model: Optional[str] = None,
        target_variant: Optional[str] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeAWS` object for use when performing dynamic AI generation using the `generative-aws` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-aws)
        for detailed usage.

        Args:
            endpoint: The endpoint to use when requesting the generation. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            region: The AWS region to run the model from. Defaults to `None`, which uses the server-defined default
            target_model: The target model to use. Defaults to `None`, which uses the server-defined default
            target_variant: The target variant to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_k: The top K to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server
            stop_sequences: The stop sequences to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeAWS(
            model=None,
            max_tokens=max_tokens,
            region=region,
            service="sagemaker",
            endpoint=TypeAdapter(AnyHttpUrl).validate_python(endpoint)
            if endpoint is not None
            else None,
            target_model=target_model,
            target_variant=target_variant,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            stop_sequences=stop_sequences,
        )

    @staticmethod
    def cohere(
        *,
        base_url: Optional[str] = None,
        k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeCohere` object for use when performing AI generation using the `generative-cohere` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-cohere)
        for detailed usage.

        Args:
            base_url: The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            k: The top K property to use. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            p: The top P property to use. Defaults to `None`, which uses the server-defined default
            presence_penalty: The presence penalty to use. Defaults to `None`, which uses the server-defined default
            stop_sequences: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeCohere(
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            k=k,
            max_tokens=max_tokens,
            model=model,
            p=p,
            presence_penalty=presence_penalty,
            stop_sequences=stop_sequences,
            temperature=temperature,
        )

    @staticmethod
    def contextualai(
        *,
        model: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        system_prompt: Optional[str] = None,
        avoid_commentary: Optional[bool] = None,
        knowledge: Optional[List[str]] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeContextualAI` object for use with the `generative-contextualai` module.

        Args:
            model: The model to use. Defaults to `None`, which uses the server-defined default
            max_new_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
            system_prompt: The system prompt to prepend to the conversation
            avoid_commentary: Whether to avoid model commentary in responses
            knowledge: Optional knowledge array to override the default knowledge from retrieved objects
        """
        return _GenerativeContextualAI(
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=max_new_tokens,
            system_prompt=system_prompt,
            avoid_commentary=avoid_commentary,
            knowledge=knowledge,
        )

    @staticmethod
    def databricks(
        *,
        endpoint: str,
        frequency_penalty: Optional[float] = None,
        log_probs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_log_probs: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeDatabricks` object for use when performing AI generation using the `generative-databricks` module.

        Args:
            endpoint: The URL where the API request should go. Defaults to `None`, which uses the server-defined default
            frequency_penalty: The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            log_probs: Whether to log probabilities. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            n: The number of sequences to generate. Defaults to `None`, which uses the server-defined default
            presence_penalty: The presence penalty to use. Defaults to `None`, which uses the server-defined default
            stop: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_log_probs: The top log probabilities to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeDatabricks(
            endpoint=TypeAdapter(AnyHttpUrl).validate_python(endpoint),
            frequency_penalty=frequency_penalty,
            log_probs=log_probs,
            max_tokens=max_tokens,
            model=model,
            n=n,
            presence_penalty=presence_penalty,
            stop=stop,
            temperature=temperature,
            top_log_probs=top_log_probs,
            top_p=top_p,
        )

    @staticmethod
    def dummy() -> _GenerativeConfigRuntime:
        """Create a `_GenerativeDummy` object for use when performing AI generation using the `generative-dummy` module."""
        return _GenerativeDummy()

    @staticmethod
    def friendliai(
        *,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        n: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeFriendliai` object for use when performing AI generation using the `generative-friendliai` module.

        Args:
            base_url: The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            n: The number of sequences to generate. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeFriendliai(
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            max_tokens=max_tokens,
            model=model,
            n=n,
            temperature=temperature,
            top_p=top_p,
        )

    @staticmethod
    @typing_deprecated(
        "`google()` is deprecated and will be removed after Q3 '26. Use a service-specific method instead, such as `google_vertex` or `google_gemini`."
    )
    def google(
        *,
        api_endpoint: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        presence_penalty: Optional[float] = None,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeGoogle` object for use when performing AI generation using the `generative-google` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/generative)
        for detailed usage.

        Args:
            api_endpoint: The API endpoint to use. Defaults to `None`, which uses the server-defined default
            endpoint_id: The endpoint ID to use. Defaults to `None`, which uses the server-defined default
            frequency_penalty: The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model ID to use. Defaults to `None`, which uses the server-defined default
            presence_penalty: The presence penalty to use. Defaults to `None`, which uses the server-defined default
            project_id: The project ID to use. Defaults to `None`, which uses the server-defined default
            region: The region to use. Defaults to `None`, which uses the server-defined default
            stop_sequences: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_k: The top K to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeGoogle(
            api_endpoint=TypeAdapter(AnyHttpUrl).validate_python(api_endpoint)
            if api_endpoint is not None
            else None,
            endpoint_id=endpoint_id,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            model=model,
            presence_penalty=presence_penalty,
            project_id=project_id,
            region=region,
            stop_sequences=stop_sequences,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

    @staticmethod
    def google_vertex(
        *,
        api_endpoint: Optional[str] = None,
        project_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        region: Optional[str] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        presence_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeGoogle` object for use when performing AI generation using the `generative-google` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/generative)
        for detailed usage.

        Args:
            api_endpoint: The API endpoint to use. Defaults to `None`, which uses the server-defined default
            endpoint_id: The endpoint ID to use. Defaults to `None`, which uses the server-defined default
            frequency_penalty: The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model ID to use. Defaults to `None`, which uses the server-defined default
            presence_penalty: The presence penalty to use. Defaults to `None`, which uses the server-defined default
            project_id: The project ID to use. Defaults to `None`, which uses the server-defined default
            region: The region to use. Defaults to `None`, which uses the server-defined default
            stop_sequences: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_k: The top K to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeGoogle(
            api_endpoint=TypeAdapter(AnyHttpUrl).validate_python(api_endpoint)
            if api_endpoint is not None
            else None,
            endpoint_id=endpoint_id,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            model=model,
            presence_penalty=presence_penalty,
            project_id=project_id,
            region=region,
            stop_sequences=stop_sequences,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

    @staticmethod
    def google_gemini(
        *,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        presence_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeGoogle` object for use when performing AI generation using the `generative-google` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/generative)
        for detailed usage.

        Args:
            frequency_penalty: The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model ID to use. Defaults to `None`, which uses the server-defined default
            presence_penalty: The presence penalty to use. Defaults to `None`, which uses the server-defined default
            stop_sequences: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_k: The top K to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeGoogle(
            api_endpoint=TypeAdapter(AnyHttpUrl).validate_python(
                "https://generativelanguage.googleapis.com"
            ),
            endpoint_id=None,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            model=model,
            presence_penalty=presence_penalty,
            project_id=None,
            region=None,
            stop_sequences=stop_sequences,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

    @staticmethod
    def mistral(
        *,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeMistral` object for use when performing AI generation using the `generative-mistral` module.

        Args:
            base_url: The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeMistral(
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            max_tokens=max_tokens,
            model=model,
            temperature=temperature,
            top_p=top_p,
        )

    @staticmethod
    def nvidia(
        *,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeNvidia` object for use when performing AI generation using the `generative-nvidia` module.

        Args:
            base_url: The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeNvidia(
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            max_tokens=max_tokens,
            model=model,
            temperature=temperature,
            top_p=top_p,
        )

    @staticmethod
    def ollama(
        *,
        api_endpoint: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeOllama` object for use when performing AI generation using the `generative-ollama` module.

        Args:
            api_endpoint: The API endpoint to use. Defaults to `None`, which uses the server-defined default
                Docker users may need to specify an alias, such as `http://host.docker.internal:11434` so that the container can access the host machine.
            model: The model to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            images: Any query-specific external images to use in the generation. Passing a string will assume a path to the image file and, if not found, will be treated as a base64-encoded string.
                The number of images passed to the prompt will match the length of this field.
            grouped_task_image_properties: Any internal image properties to use in the generation sourced from the object's properties returned by the retrieval step.
                The number of images passed to the prompt will match the value of `limit` in the search query.
        """
        return _GenerativeOllama(
            api_endpoint=TypeAdapter(AnyHttpUrl).validate_python(api_endpoint)
            if api_endpoint is not None
            else None,
            model=model,
            temperature=temperature,
        )

    @staticmethod
    def openai(
        *,
        api_version: Optional[str] = None,
        base_url: Optional[str] = None,
        deployment_id: Optional[str] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        presence_penalty: Optional[float] = None,
        reasoning_effort: Optional[Union[OpenAiReasoningEffort, str]] = None,
        resource_name: Optional[str] = None,
        stop: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        verbosity: Optional[Union[OpenAiVerbosity, str]] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeOpenAI` object for use when performing AI generation using the OpenAI-backed `generative-openai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai)
        for detailed usage.

        Args:
            api_version: The API version to use. Defaults to `None`, which uses the server-defined default
            base_url: The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            deployment_id: The deployment ID to use. Defaults to `None`, which uses the server-defined default
            frequency_penalty: The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            presence_penalty: The presence penalty to use. Defaults to `None`, which uses the server-defined default
            reasoning_effort: The reasoning effort to use. Defaults to `None`, which uses the server-defined default
            resource_name: The name of the OpenAI resource to use. Defaults to `None`, which uses the server-defined default
            stop: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
            verbosity: The verbosity to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeOpenAI(
            api_version=api_version,
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            deployment_id=deployment_id,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            model=model,
            presence_penalty=presence_penalty,
            resource_name=resource_name,
            stop=stop,
            temperature=temperature,
            top_p=top_p,
            is_azure=False,
            verbosity=verbosity,
            reasoning_effort=reasoning_effort,
        )

    @staticmethod
    def azure_openai(
        *,
        api_version: Optional[str] = None,
        base_url: Optional[str] = None,
        deployment_id: Optional[str] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        presence_penalty: Optional[float] = None,
        resource_name: Optional[str] = None,
        stop: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeOpenAI` object for use when performing AI generation using the Azure-backed `generative-openai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai)
        for detailed usage.

        Args:
            api_version: The API version to use. Defaults to `None`, which uses the server-defined default
            base_url: The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            deployment_id: The deployment ID to use. Defaults to `None`, which uses the server-defined default
            frequency_penalty: The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            presence_penalty: The presence penalty to use. Defaults to `None`, which uses the server-defined default
            resource_name: The name of the OpenAI resource to use. Defaults to `None`, which uses the server-defined default
            stop: The stop sequences to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeOpenAI(
            api_version=api_version,
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            deployment_id=deployment_id,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            model=model,
            presence_penalty=presence_penalty,
            resource_name=resource_name,
            stop=stop,
            temperature=temperature,
            top_p=top_p,
            is_azure=True,
            verbosity=None,
            reasoning_effort=None,
        )

    @staticmethod
    def xai(
        *,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigRuntime:
        """Create a `_GenerativeXAI` object for use when performing AI generation using the `generative-xai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-xai)
        for detailed usage.

        Args:
            base_url: The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            max_tokens: The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            model: The model to use. Defaults to `None`, which uses the server-defined default
            temperature: The temperature to use. Defaults to `None`, which uses the server-defined default
            top_p: The top P to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeXAI(
            base_url=TypeAdapter(AnyHttpUrl).validate_python(base_url)
            if base_url is not None
            else None,
            max_tokens=max_tokens,
            model=model,
            temperature=temperature,
            top_p=top_p,
        )


class _GroupedTask(BaseModel):
    prompt: str
    non_blob_properties: Optional[List[str]]
    image_properties: Optional[List[str]]
    images: Optional[Iterable[str]]
    metadata: bool = False

    def _to_grpc(
        self, provider: _GenerativeConfigRuntime
    ) -> generative_pb2.GenerativeSearch.Grouped:
        return generative_pb2.GenerativeSearch.Grouped(
            task=self.prompt,
            properties=_to_text_array(self.non_blob_properties),
            queries=[
                provider._to_grpc(
                    _GenerativeConfigRuntimeOptions(
                        self.metadata, self.images, self.image_properties
                    )
                )
            ],
        )


class _SinglePrompt(BaseModel):
    prompt: str
    image_properties: Optional[List[str]]
    images: Optional[Iterable[str]]
    metadata: bool = False
    debug: bool = False

    def _to_grpc(
        self, provider: _GenerativeConfigRuntime
    ) -> generative_pb2.GenerativeSearch.Single:
        return generative_pb2.GenerativeSearch.Single(
            prompt=self.prompt,
            debug=self.debug,
            queries=[
                provider._to_grpc(
                    _GenerativeConfigRuntimeOptions(
                        self.metadata, self.images, self.image_properties
                    )
                )
            ],
        )


GroupedTask = _GroupedTask
SinglePrompt = _SinglePrompt


class GenerativeParameters:
    """Factory class for creating `_GroupedTask` and `_SinglePrompt` objects for use in the `generate` namespace."""

    @staticmethod
    def grouped_task(
        prompt: str,
        *,
        non_blob_properties: Optional[List[str]] = None,
        image_properties: Optional[List[str]] = None,
        images: Optional[Union[BLOB_INPUT, Iterable[BLOB_INPUT]]] = None,
        metadata: bool = False,
    ) -> _GroupedTask:
        """Create a `_GroupedTask` object for use when performing AI generation using the `generate` namespace and the `grouped_task` field."""
        return _GroupedTask(
            prompt=prompt,
            non_blob_properties=non_blob_properties,
            image_properties=image_properties,
            images=GenerativeParameters.__parse_images(images),
            metadata=metadata,
        )

    @staticmethod
    def single_prompt(
        prompt: str,
        *,
        image_properties: Optional[List[str]] = None,
        images: Optional[Union[BLOB_INPUT, Iterable[BLOB_INPUT]]] = None,
        metadata: bool = False,
        debug: bool = False,
    ) -> _SinglePrompt:
        """Create a `_SinglePrompt` object for use when performing AI generation using the `generate` namespace and the `single_prompt` field."""
        return _SinglePrompt(
            prompt=prompt,
            image_properties=image_properties,
            images=GenerativeParameters.__parse_images(images),
            metadata=metadata,
            debug=debug,
        )

    @staticmethod
    def __parse_images(
        images: Optional[Union[BLOB_INPUT, Iterable[BLOB_INPUT]]],
    ) -> Optional[Iterable[str]]:
        if isinstance(images, (str, Path, BufferedReader)):
            return (
                parse_blob(images) for _ in "."
            )  # creates an Iterable[str]-compatible Generator with a single element
        return (parse_blob(image) for image in images) if images is not None else None
