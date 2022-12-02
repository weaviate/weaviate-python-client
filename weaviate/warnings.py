import warnings

import weaviate.version as version


class _Warnings:
    @staticmethod
    def auth_with_anon_weaviate():
        warnings.warn(
            message="""Auth001: The client was configured to use authentication, but weaviate is configured without
                    authentication. Are you sure this is correct?""",
            category=UserWarning,
            stacklevel=1,
        )

    @staticmethod
    def weaviate_server_older_than_1_14(server_version: str):
        warnings.warn(
            message=f"""Dep001: You are using the Weaviate Python Client version {version.__version__} which supports
            changes and features of Weaviate >=1.14.x, but you are connected to Weaviate {server_version}.
            If you want to make use of these new changes/features using this Python Client version, upgrade your
            Weaviate instance.""",
            category=DeprecationWarning,
            stacklevel=1,
        )
