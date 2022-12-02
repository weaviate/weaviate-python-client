import warnings


class _Warnings:
    @staticmethod
    def auth_with_anon_weaviate():
        warnings.warn(
            message="""Auth001: The client was configured to use authentication, but weaviate is configured without
                    authentication. Are you sure this is correct?""",
            category=UserWarning,
            stacklevel=1,
        )
