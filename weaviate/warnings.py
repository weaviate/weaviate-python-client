import warnings
from importlib.metadata import version, PackageNotFoundError
from typing import Optional

try:
    __version__ = version("weaviate")
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
