import warnings
from datetime import datetime
from importlib.metadata import version, PackageNotFoundError
from typing import Literal, Optional

try:
    __version__ = version("weaviate-client")
except PackageNotFoundError:
    __version__ = "unknown version"


class _Warnings:
    @staticmethod
    def auth_with_anon_weaviate() -> None:
        warnings.warn(
            message="""Auth001: The client was configured to use authentication, but weaviate is configured without
                    authentication. Are you sure this is correct?""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def auth_no_refresh_token(auth_len: Optional[int] = None) -> None:
        if auth_len is not None:
            msg = f"The current access token is only valid for {auth_len}s."
        else:
            msg = "Also, no expiration time was given."

        warnings.warn(
            message=f"""Auth002: The token returned from you identity provider does not contain a refresh token. {msg}

            Access to your weaviate instance is not possible after expiration and this client will return an
            authentication exception.

            Things to try:
            - You might need to enable refresh tokens in the settings of your authentication provider
            - You might need to send the correct scope. For some providers it needs to include "offline_access"
            """,
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def auth_negative_expiration_time(expires_in: int) -> None:
        msg = f"""Auth003: Access token expiration time is negative: {expires_in}."""

        warnings.warn(message=msg, category=UserWarning, stacklevel=1)

    @staticmethod
    def auth_header_and_auth_secret() -> None:
        msg = """Auth004: Received an authentication header and an auth_client_secret parameter.

         The auth_client_secret takes precedence over the header and the authentication header will be ignored. Use
         weaviate.auth.AuthBearerToken(..) to supply an access token via auth_client_secret parameter and (if available)
         also supply refresh tokens and token lifetimes.
         """
        warnings.warn(message=msg, category=UserWarning, stacklevel=1)

    @staticmethod
    def auth_cannot_parse_oidc_config(url: str) -> None:
        msg = f"""Auth005: Could not parse Weaviates OIDC configuration, using unauthenticated access. If you added
        an authorization header yourself it will be unaffected.

        This can happen if weaviate is miss-configured or you have a proxy inbetween the client and weaviate.
        You can test this by visiting {url}."""
        warnings.warn(message=msg, category=UserWarning, stacklevel=1)

    @staticmethod
    def weaviate_server_older_than_1_14(server_version: str) -> None:
        warnings.warn(
            message=f"""Dep001: You are using the Weaviate Python Client version {__version__} which supports
            changes and features of Weaviate >=1.14.x, but you are connected to Weaviate {server_version}.
            If you want to make use of these new changes/features using this Python Client version, upgrade your
            Weaviate instance.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def manual_batching() -> None:
        warnings.warn(
            message="""Dep002: You are batching manually. This means you are NOT using the client's built-in
            multi-threading. Setting `batch_size` in `client.batch.configure()`  to an int value will enabled automatic
            batching. See:
            https://weaviate.io/developers/weaviate/current/restful-api-references/batch.html#example-request-1""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def weaviate_too_old_for_openai(server_version: str) -> None:
        warnings.warn(
            message=f"""Dep003: You are trying to use the generative search, but you are connected to Weaviate {server_version}.
            Support for generative search was added in weaviate version 1.17.3.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def token_refresh_failed(exc: Exception) -> None:
        warnings.warn(
            message=f"""Con001: Could not reach token issuer for the periodic refresh. This client will automatically
            retry to refresh. If this does not succeed, the client will become unauthenticated.
            Causes might be an unstable internet connection or a problem with your authentication provider.
            Exception: {exc}
            """,
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def weaviate_too_old_vs_latest(server_version: str) -> None:
        warnings.warn(
            message=f"""Dep004: You are connected to Weaviate {server_version}.
            Please consider upgrading to the latest version. See https://www.weaviate.io/developers/weaviate for details.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def weaviate_client_too_old_vs_latest(client_version: str, latest_version: str) -> None:
        warnings.warn(
            message=f"""Dep005: You are using weaviate-client version {client_version}. The latest version is {latest_version}.
            Please consider upgrading to the latest version. See https://weaviate.io/developers/weaviate/client-libraries/python for details.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def use_of_client_batch_will_be_removed_in_next_major_release() -> None:
        warnings.warn(
            message="""Dep006: You are using the `client.batch()` method, which will be removed in the next major release.
            Please instead use the `client.batch.configure()` method to configure your batch and `client.batch` to enter the context manager.
            See https://weaviate.io/developers/weaviate/client-libraries/python for details.""",
            category=DeprecationWarning,
            stacklevel=1,
        )

    @staticmethod
    def datetime_insertion_with_no_specified_timezone(date: datetime) -> None:
        warnings.warn(
            message=f"""Con002: You are inserting the datetime object {date} without a timezone. The timezone will be set to UTC.
            If you want to use a different timezone, please specify it in the datetime object. For example:
            datetime.datetime(2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone(-datetime.timedelta(hours=2))).isoformat() = 2021-01-01T00:00:00-02:00
            """,
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def text2vec_huggingface_endpoint_url_and_model_set_together() -> None:
        warnings.warn(
            message="""Con003: You are setting the endpoint_url alongside model or passage_model & query_model in your Text2Vec-HuggingFace module configuration.
            The model definitions will be ignored in favour of endpoint_url.
            """,
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_executor_is_shutdown() -> None:
        warnings.warn(
            message="""Bat001: The BatchExecutor was shutdown, most probably when it exited the `with` statement.
                It will be initialized again. If you are not `batch` in the `with client.batch as batch`
                please make sure to shut it down when done importing data: `client.batch.shutdown()`.
                You can start it again using the `client.batch.start()` method.""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_weaviate_overloaded_sleeping(sleep: int) -> None:
        warnings.warn(
            message=f"""Bat002: Weaviate is currently overloaded. Sleeping for {sleep} seconds.""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_refresh_failed(err: str) -> None:
        warnings.warn(
            message=f"""Bat003: The dynamic batch-size could not be refreshed successfully. Algorithm backing off by 10 seconds. {err}""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_retrying_failed_batches_hit_hard_limit(limit: int) -> None:
        warnings.warn(
            message=f"""Bat004: Attempts to retry failed objects and/or references have hit the hard limit of {limit}.
            The failed objects and references can be accessed in client.collections.batch.failed_objects and client.collections.batch.failed_references.""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def batch_create_automatic(type_: Literal["objects", "references"]) -> None:
        warnings.warn(
            message=f"""You are tying to manually create {type_} in an automatic batching environment. If you want to do manual batching, you need to use
            client.batch.configure() to return a new Batch object with `dynamic=False` and `batch_size=None`.""",
            category=UserWarning,
            stacklevel=1,
        )
