from typing import Dict, Optional, cast

from pydantic import BaseModel, ConfigDict, Field


class _IntegrationConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    def _to_header(self) -> Dict[str, str]:
        # headers have to be strings
        return_dict = cast(dict, self.model_dump(by_alias=True, exclude_none=True))
        for key, value in return_dict.items():
            return_dict[key] = str(value)

        return return_dict


class _IntegrationConfigCohere(_IntegrationConfig):
    api_key: str = Field(serialization_alias="X-Cohere-Api-Key")
    requests_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Cohere-Ratelimit-RequestPM-Embedding"
    )
    base_url: Optional[str] = Field(serialization_alias="X-Cohere-Baseurl")


class _IntegrationConfigHuggingface(_IntegrationConfig):
    api_key: str = Field(serialization_alias="X-Huggingface-Api-Key")
    requests_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Huggingface-Ratelimit-RequestPM-Embedding"
    )
    base_url: Optional[str] = Field(serialization_alias="X-Huggingface-Baseurl")


class _IntegrationConfigOpenAi(_IntegrationConfig):
    api_key: str = Field(serialization_alias="X-Openai-Api-Key")
    organization: Optional[str] = Field(serialization_alias="X-Openai-Organization")
    requests_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Openai-Ratelimit-RequestPM-Embedding"
    )
    tokens_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Openai-Ratelimit-TokenPM-Embedding"
    )
    base_url: Optional[str] = Field(serialization_alias="X-Openai-Baseurl")


class _IntegrationConfigAWS(_IntegrationConfig):
    access_key: str = Field(serialization_alias="X-Aws-Access-Key")
    secret_key: str = Field(serialization_alias="X-Aws-Secret-Key")
    requests_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Aws-Ratelimit-RequestPM-Embedding"
    )
    tokens_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Aws-Ratelimit-TokensPM-Embedding"
    )


class _IntegrationConfigVoyage(_IntegrationConfig):
    api_key: str = Field(serialization_alias="X-Voyageai-Api-Key")
    requests_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Voyageai-Ratelimit-RequestPM-Embedding"
    )
    tokens_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Voyageai-Ratelimit-TokenPM-Embedding"
    )
    base_url: Optional[str] = Field(serialization_alias="X-Voyageai-Baseurl")


class _IntegrationConfigJina(_IntegrationConfig):
    api_key: str = Field(serialization_alias="X-Jinaai-Api-Key")
    requests_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-Jinaai-Ratelimit-RequestPM-Embedding"
    )
    base_url: Optional[str] = Field(serialization_alias="X-Jinaai-Baseurl")


class _IntegrationConfigOcto(_IntegrationConfig):
    api_key: str = Field(serialization_alias="X-OctoAI-Api-Key")
    requests_per_minute_embeddings: Optional[int] = Field(
        serialization_alias="X-OctoAI-Ratelimit-RequestPM-Embedding"
    )
    base_url: Optional[str] = Field(serialization_alias="X-OctoAI-Baseurl")


class Integrations:
    @staticmethod
    def cohere(
        *,
        api_key: str,
        base_url: Optional[str] = None,
        requests_per_minute_embeddings: Optional[int] = None
    ) -> _IntegrationConfig:
        return _IntegrationConfigCohere(
            api_key=api_key,
            requests_per_minute_embeddings=requests_per_minute_embeddings,
            base_url=base_url,
        )

    @staticmethod
    def huggingface(
        *,
        api_key: str,
        requests_per_minute_embeddings: Optional[int] = None,
        base_url: Optional[str] = None
    ) -> _IntegrationConfig:
        return _IntegrationConfigHuggingface(
            api_key=api_key,
            requests_per_minute_embeddings=requests_per_minute_embeddings,
            base_url=base_url,
        )

    @staticmethod
    def openai(
        *,
        api_key: str,
        requests_per_minute_embeddings: Optional[int] = None,
        tokens_per_minute_embeddings: Optional[int] = None,
        organization: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> _IntegrationConfig:
        return _IntegrationConfigOpenAi(
            api_key=api_key,
            requests_per_minute_embeddings=requests_per_minute_embeddings,
            tokens_per_minute_embeddings=tokens_per_minute_embeddings,
            organization=organization,
            base_url=base_url,
        )

    # not yet implemented
    # @staticmethod
    # def aws(
    #     *,
    #     access_key: str,
    #     secret_key: str,
    #     requests_per_minute_embeddings: Optional[int] = None,
    #     tokens_per_minute_embeddings: Optional[int] = None,
    # ) -> _IntegrationConfig:
    #     return _IntegrationConfigAWS(
    #         access_key=access_key,
    #         secret_key=secret_key,
    #         requests_per_minute_embeddings=requests_per_minute_embeddings,
    #         tokens_per_minute_embeddings=tokens_per_minute_embeddings,
    #     )

    @staticmethod
    def voyageai(
        *,
        api_key: str,
        requests_per_minute_embeddings: Optional[int] = None,
        tokens_per_minute_embeddings: Optional[int] = None,
        base_url: Optional[str] = None
    ) -> _IntegrationConfig:
        return _IntegrationConfigVoyage(
            api_key=api_key,
            requests_per_minute_embeddings=requests_per_minute_embeddings,
            tokens_per_minute_embeddings=tokens_per_minute_embeddings,
            base_url=base_url,
        )

    @staticmethod
    def jinaai(
        *,
        api_key: str,
        requests_per_minute_embeddings: Optional[int] = None,
        base_url: Optional[str] = None
    ) -> _IntegrationConfig:
        return _IntegrationConfigJina(
            api_key=api_key,
            requests_per_minute_embeddings=requests_per_minute_embeddings,
            base_url=base_url,
        )

    @staticmethod
    def octoai(
        *,
        api_key: str,
        requests_per_minute_embeddings: Optional[int] = None,
        base_url: Optional[str] = None
    ) -> _IntegrationConfig:
        return _IntegrationConfigOcto(
            api_key=api_key,
            requests_per_minute_embeddings=requests_per_minute_embeddings,
            base_url=base_url,
        )
