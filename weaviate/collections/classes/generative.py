from collections.abc import Iterable
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, AnyUrl, BaseModel, Field

from weaviate.collections.classes.config import (
    GenerativeSearches,
    _EnumLikeStr,
    AWSService,
    CohereModel,
)
from weaviate.proto.v1.base_pb2 import TextArray
from weaviate.proto.v1.generative_pb2 import (
    GenerativeAnthropic,
    GenerativeAnyscale,
    GenerativeAWS,
    GenerativeCohere,
    GenerativeDatabricks,
    GenerativeDummy,
    GenerativeFriendliAI,
    GenerativeGoogle,
    GenerativeMistral,
    GenerativeNvidia,
    GenerativeOllama,
    GenerativeOpenAI,
    GenerativeProvider as GenerativeProviderGRPC,
)
from weaviate.types import BLOB_INPUT
from weaviate.util import parse_blob


class _GenerativeProviderDynamic(BaseModel):
    generative: Union[GenerativeSearches, _EnumLikeStr]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        raise NotImplementedError("This method must be implemented in the child class")

    def _parse_anyhttpurl(self, url: Optional[AnyHttpUrl]) -> Optional[str]:
        return str(url) if url is not None else None

    def _to_text_array(self, values: Optional[Iterable[str]]) -> Optional[TextArray]:
        return TextArray(values=values) if values is not None else None


GenerativeProviderDynamic = _GenerativeProviderDynamic


class _GenerativeAnthropic(_GenerativeProviderDynamic):
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
    images: Optional[Iterable[str]]
    image_properties: Optional[List[str]]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            anthropic=GenerativeAnthropic(
                base_url=self._parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
                stop_sequences=self._to_text_array(self.stop_sequences),
                images=self._to_text_array(self.images),
                image_properties=self._to_text_array(self.image_properties),
            ),
        )


class _GenerativeAnyscale(_GenerativeProviderDynamic):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.ANYSCALE, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    model: Optional[str]
    temperature: Optional[float]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            anyscale=GenerativeAnyscale(
                base_url=self._parse_anyhttpurl(self.base_url),
                model=self.model,
                temperature=self.temperature,
            ),
        )


class _GenerativeAWS(_GenerativeProviderDynamic):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.AWS, frozen=True, exclude=True
    )
    model: Optional[str]
    region: Optional[str]
    endpoint: Optional[AnyHttpUrl]
    service: Optional[str]
    target_model: Optional[str]
    target_variant: Optional[str]
    temperature: Optional[float]
    images: Optional[Iterable[str]]
    image_properties: Optional[List[str]]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            aws=GenerativeAWS(
                model=self.model,
                region=self.region,
                endpoint=self._parse_anyhttpurl(self.endpoint),
                service=self.service,
                target_model=self.target_model,
                target_variant=self.target_variant,
                temperature=self.temperature,
                images=self._to_text_array(self.images),
                image_properties=self._to_text_array(self.image_properties),
            ),
        )


class _GenerativeCohere(_GenerativeProviderDynamic):
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

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            cohere=GenerativeCohere(
                base_url=self._parse_anyhttpurl(self.base_url),
                k=self.k,
                max_tokens=self.max_tokens,
                model=self.model,
                p=self.p,
                presence_penalty=self.presence_penalty,
                stop_sequences=self._to_text_array(self.stop_sequences),
                temperature=self.temperature,
            ),
        )


class _GenerativeDatabricks(_GenerativeProviderDynamic):
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

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            databricks=GenerativeDatabricks(
                endpoint=self._parse_anyhttpurl(self.endpoint),
                frequency_penalty=self.frequency_penalty,
                log_probs=self.log_probs or False,
                max_tokens=self.max_tokens,
                model=self.model,
                n=self.n,
                presence_penalty=self.presence_penalty,
                stop=self._to_text_array(self.stop),
                temperature=self.temperature,
                top_log_probs=self.top_log_probs,
                top_p=self.top_p,
            ),
        )


class _GenerativeDummy(_GenerativeProviderDynamic):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.DUMMY, frozen=True, exclude=True
    )

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(return_metadata=return_metadata, dummy=GenerativeDummy())


class _GenerativeFriendliai(_GenerativeProviderDynamic):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.FRIENDLIAI, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    n: Optional[int]
    temperature: Optional[float]
    top_p: Optional[float]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            friendliai=GenerativeFriendliAI(
                base_url=self._parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                n=self.n,
                temperature=self.temperature,
                top_p=self.top_p,
            ),
        )


class _GenerativeMistral(_GenerativeProviderDynamic):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.MISTRAL, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            mistral=GenerativeMistral(
                base_url=self._parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
            ),
        )


class _GenerativeNvidia(_GenerativeProviderDynamic):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.NVIDIA, frozen=True, exclude=True
    )
    base_url: Optional[AnyHttpUrl]
    max_tokens: Optional[int]
    model: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            nvidia=GenerativeNvidia(
                base_url=self._parse_anyhttpurl(self.base_url),
                max_tokens=self.max_tokens,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
            ),
        )


class _GenerativeOllama(_GenerativeProviderDynamic):
    generative: Union[GenerativeSearches, _EnumLikeStr] = Field(
        default=GenerativeSearches.OLLAMA, frozen=True, exclude=True
    )
    api_endpoint: Optional[AnyHttpUrl]
    model: Optional[str]
    temperature: Optional[float]
    images: Optional[Iterable[str]]
    image_properties: Optional[List[str]]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            ollama=GenerativeOllama(
                api_endpoint=self._parse_anyhttpurl(self.api_endpoint),
                model=self.model,
                temperature=self.temperature,
                images=self._to_text_array(self.images),
                image_properties=self._to_text_array(self.image_properties),
            ),
        )


class _GenerativeOpenAI(_GenerativeProviderDynamic):
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
    images: Optional[Iterable[str]]
    image_properties: Optional[List[str]]

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            openai=GenerativeOpenAI(
                api_version=self.api_version,
                base_url=self._parse_anyhttpurl(self.base_url),
                deployment_id=self.deployment_id,
                frequency_penalty=self.frequency_penalty,
                max_tokens=self.max_tokens,
                model=self.model,
                presence_penalty=self.presence_penalty,
                resource_name=self.resource_name,
                stop=self._to_text_array(self.stop),
                temperature=self.temperature,
                top_p=self.top_p,
                is_azure=self.is_azure,
                images=self._to_text_array(self.images),
                image_properties=self._to_text_array(self.image_properties),
            ),
        )


class _GenerativeGoogle(_GenerativeProviderDynamic):
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
    images: Optional[Iterable[str]]
    image_properties: Optional[List[str]]

    def _parse_api_endpoint(self, url: Optional[AnyHttpUrl]) -> Optional[str]:
        return (
            u.replace("https://", "").replace("http://", "")
            if (u := self._parse_anyhttpurl(url)) is not None
            else None
        )

    def to_grpc(self, return_metadata: bool) -> GenerativeProviderGRPC:
        return GenerativeProviderGRPC(
            return_metadata=return_metadata,
            google=GenerativeGoogle(
                api_endpoint=self._parse_api_endpoint(self.api_endpoint),
                endpoint_id=self.endpoint_id,
                frequency_penalty=self.frequency_penalty,
                max_tokens=self.max_tokens,
                model=self.model,
                presence_penalty=self.presence_penalty,
                project_id=self.project_id,
                region=self.region,
                stop_sequences=self._to_text_array(self.stop_sequences),
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
                images=self._to_text_array(self.images),
                image_properties=self._to_text_array(self.image_properties),
            ),
        )


class GenerativeProvider:
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
        grouped_task_images: Optional[Iterable[str]] = None,
        grouped_task_image_properties: Optional[List[str]] = None,
    ) -> _GenerativeProviderDynamic:
        """
        Create a `_GenerativeAnthropic` object for use when performing dynamic AI generation using the `generative-anthropic` module.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `stop_sequences`
                The stop sequences to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_k`
                The top K to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P to use. Defaults to `None`, which uses the server-defined default
            `grouped_task_images`
                Any query-specific external images to use in the generation. Passing a string will assume a path to the image file and, if not found, will be treated as a base64-encoded string.
                The number of images passed to the prompt will match the length of this field.
            `grouped_task_image_properties`
                Any internal image properties to use in the generation sourced from the object's properties returned by the retrieval step.
                The number of images passed to the prompt will match the value of `limit` in the search query.
        """
        return _GenerativeAnthropic(
            base_url=AnyUrl(base_url) if base_url is not None else None,
            model=model,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            images=(
                (parse_blob(image) for image in grouped_task_images)
                if grouped_task_images is not None
                else None
            ),
            image_properties=grouped_task_image_properties,
        )

    @staticmethod
    def anyscale(
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeAnyscale` object for use when performing dynamic AI generation using the `generative-anyscale` module.

        Arguments:
            `base_url`
                The base URL to send the API request to. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeAnyscale(
            base_url=AnyUrl(base_url) if base_url is not None else None,
            model=model,
            temperature=temperature,
        )

    @staticmethod
    def aws(
        *,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        region: Optional[str] = None,
        service: Optional[Union[AWSService, str]] = None,
        target_model: Optional[str] = None,
        target_variant: Optional[str] = None,
        temperature: Optional[float] = None,
        grouped_task_images: Optional[Iterable[BLOB_INPUT]] = None,
        grouped_task_image_properties: Optional[List[str]] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeAWS` object for use when performing dynamic AI generation using the `generative-aws` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-aws)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `region`
                The AWS region to run the model from. Defaults to `None`, which uses the server-defined default
            `endpoint`
                The endpoint to use when requesting the generation. Defaults to `None`, which uses the server-defined default
            `service`
                The AWS service to use. Defaults to `None`, which uses the server-defined default
            TODO: add docs for these new params
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `images`
                Any query-specific external images to use in the generation. Passing a string will assume a path to the image file and, if not found, will be treated as a base64-encoded string.
                The number of images passed to the prompt will match the length of this field.
            `grouped_task_image_properties`
                Any internal image properties to use in the generation sourced from the object's properties returned by the retrieval step.
                The number of images passed to the prompt will match the value of `limit` in the search query.
        """
        return _GenerativeAWS(
            model=model,
            region=region,
            service=service,
            endpoint=AnyUrl(endpoint) if endpoint is not None else None,
            target_model=target_model,
            target_variant=target_variant,
            temperature=temperature,
            images=(
                (parse_blob(image) for image in grouped_task_images)
                if grouped_task_images is not None
                else None
            ),
            image_properties=grouped_task_image_properties,
        )

    @staticmethod
    def cohere(
        *,
        base_url: Optional[str] = None,
        k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        model: Optional[Union[CohereModel, str]] = None,
        p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeCohere` object for use when performing AI generation using the `generative-cohere` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-cohere)
        for detailed usage.

        Arguments:
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            `k`
                The top K property to use. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `p`
                The top P property to use. Defaults to `None`, which uses the server-defined default
            `presence_penalty`
                The presence penalty to use. Defaults to `None`, which uses the server-defined default
            `stop_sequences`
                The stop sequences to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeCohere(
            base_url=AnyUrl(base_url) if base_url is not None else None,
            k=k,
            max_tokens=max_tokens,
            model=model,
            p=p,
            presence_penalty=presence_penalty,
            stop_sequences=stop_sequences,
            temperature=temperature,
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
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeDatabricks` object for use when performing AI generation using the `generative-databricks` module.

        Arguments:
            `endpoint`
                The URL where the API request should go. Defaults to `None`, which uses the server-defined default
            `frequency_penalty`
                The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            `log_probs`
                Whether to log probabilities. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `n`
                The number of sequences to generate. Defaults to `None`, which uses the server-defined default
            `stop`
                The stop sequences to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_log_probs`
                The top log probabilities to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeDatabricks(
            endpoint=AnyUrl(endpoint),
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
    def dummy() -> _GenerativeProviderDynamic:
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
    ) -> _GenerativeProviderDynamic:
        """
        Create a `_GenerativeFriendliai` object for use when performing AI generation using the `generative-friendliai` module.

        Arguments:
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `n`
                The number of sequences to generate. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeFriendliai(
            base_url=AnyUrl(base_url) if base_url is not None else None,
            max_tokens=max_tokens,
            model=model,
            n=n,
            temperature=temperature,
            top_p=top_p,
        )

    @staticmethod
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
        grouped_task_images: Optional[Iterable[BLOB_INPUT]] = None,
        grouped_task_image_properties: Optional[List[str]] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeGoogle` object for use when performing AI generation using the `generative-google` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/generative)
        for detailed usage.

        Arguments:
            `api_endpoint`
                The API endpoint to use. Defaults to `None`, which uses the server-defined default
            `endpoint_id`
                The endpoint ID to use. Defaults to `None`, which uses the server-defined default
            `frequency_penalty`
                The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model ID to use. Defaults to `None`, which uses the server-defined default
            `presence_penalty`
                The presence penalty to use. Defaults to `None`, which uses the server-defined default
            `project_id`
                The project ID to use. Defaults to `None`, which uses the server-defined default
            `region`
                The region to use. Defaults to `None`, which uses the server-defined default
            `stop_sequences`
                The stop sequences to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_k`
                The top K to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P to use. Defaults to `None`, which uses the server-defined default
            `images`
                Any query-specific external images to use in the generation. Passing a string will assume a path to the image file and, if not found, will be treated as a base64-encoded string.
                The number of images passed to the prompt will match the length of this field.
            `grouped_task_image_properties`
                Any internal image properties to use in the generation sourced from the object's properties returned by the retrieval step.
                The number of images passed to the prompt will match the value of `limit` in the search query.
        """
        return _GenerativeGoogle(
            api_endpoint=AnyUrl(api_endpoint) if api_endpoint is not None else None,
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
            images=(
                (parse_blob(image) for image in grouped_task_images)
                if grouped_task_images is not None
                else None
            ),
            image_properties=grouped_task_image_properties,
        )

    @staticmethod
    def mistral(
        *,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeMistral` object for use when performing AI generation using the `generative-mistral` module.

        Arguments:
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeMistral(
            base_url=AnyUrl(base_url) if base_url is not None else None,
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
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeOllama` object for use when performing AI generation using the `generative-nvidia` module.

        Arguments:
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P value to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeNvidia(
            base_url=AnyUrl(base_url) if base_url is not None else None,
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
        grouped_task_images: Optional[Iterable[BLOB_INPUT]] = None,
        grouped_task_image_properties: Optional[List[str]] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeOllama` object for use when performing AI generation using the `generative-ollama` module.

        Arguments:
            `api_endpoint`
                The API endpoint to use. Defaults to `None`, which uses the server-defined default
                Docker users may need to specify an alias, such as `http://host.docker.internal:11434` so that the container can access the host machine.
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `images`
                Any query-specific external images to use in the generation. Passing a string will assume a path to the image file and, if not found, will be treated as a base64-encoded string.
                The number of images passed to the prompt will match the length of this field.
            `grouped_task_image_properties`
                Any internal image properties to use in the generation sourced from the object's properties returned by the retrieval step.
                The number of images passed to the prompt will match the value of `limit` in the search query.
        """
        return _GenerativeOllama(
            api_endpoint=AnyUrl(api_endpoint) if api_endpoint is not None else None,
            model=model,
            temperature=temperature,
            images=(
                (parse_blob(image) for image in grouped_task_images)
                if grouped_task_images is not None
                else None
            ),
            image_properties=grouped_task_image_properties,
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
        resource_name: Optional[str] = None,
        stop: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        grouped_task_images: Optional[Iterable[BLOB_INPUT]] = None,
        grouped_task_image_properties: Optional[List[str]] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeOpenAI` object for use when performing AI generation using the OpenAI-backed `generative-openai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai)
        for detailed usage.

        Arguments:
            `api_version`
                The API version to use. Defaults to `None`, which uses the server-defined default
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            `deployment_id`
                The deployment ID to use. Defaults to `None`, which uses the server-defined default
            `frequency_penalty`
                The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `presence_penalty`
                The presence penalty to use. Defaults to `None`, which uses the server-defined default
            `resource_name`
                The name of the OpenAI resource to use. Defaults to `None`, which uses the server-defined default
            `stop`
                The stop sequences to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P to use. Defaults to `None`, which uses the server-defined default
            `images`
                Any query-specific external images to use in the generation. Passing a string will assume a path to the image file and, if not found, will be treated as a base64-encoded string.
                The number of images passed to the prompt will match the length of this field.
            `grouped_task_image_properties`
                Any internal image properties to use in the generation sourced from the object's properties returned by the retrieval step.
                The number of images passed to the prompt will match the value of `limit` in the search query.

        """
        return _GenerativeOpenAI(
            api_version=api_version,
            base_url=AnyUrl(base_url) if base_url is not None else None,
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
            images=(
                (parse_blob(image) for image in grouped_task_images)
                if grouped_task_images is not None
                else None
            ),
            image_properties=grouped_task_image_properties,
        )

    @staticmethod
    def openai_azure(
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
        grouped_task_images: Optional[Iterable[BLOB_INPUT]] = None,
        grouped_task_image_properties: Optional[List[str]] = None,
    ) -> _GenerativeProviderDynamic:
        """Create a `_GenerativeOpenAI` object for use when performing AI generation using the Azure-backed `generative-openai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai)
        for detailed usage.

        Arguments:
            `api_version`
                The API version to use. Defaults to `None`, which uses the server-defined default
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
            `deployment_id`
                The deployment ID to use. Defaults to `None`, which uses the server-defined default
            `frequency_penalty`
                The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `presence_penalty`
                The presence penalty to use. Defaults to `None`, which uses the server-defined default
            `resource_name`
                The name of the OpenAI resource to use. Defaults to `None`, which uses the server-defined default
            `stop`
                The stop sequences to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P to use. Defaults to `None`, which uses the server-defined default
            `images`
                Any query-specific external images to use in the generation. Passing a string will assume a path to the image file and, if not found, will be treated as a base64-encoded string.
                The number of images passed to the prompt will match the length of this field.
            `grouped_task_image_properties`
                Any internal image properties to use in the generation sourced from the object's properties returned by the retrieval step.
                The number of images passed to the prompt will match the value of `limit` in the search query.
        """
        return _GenerativeOpenAI(
            api_version=api_version,
            base_url=AnyUrl(base_url) if base_url is not None else None,
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
            images=(
                (parse_blob(image) for image in grouped_task_images)
                if grouped_task_images is not None
                else None
            ),
            image_properties=grouped_task_image_properties,
        )
