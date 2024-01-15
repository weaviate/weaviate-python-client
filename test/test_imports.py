import pytest
import warnings


def test_deprecated_imports() -> None:
    with pytest.warns(DeprecationWarning) as recwarn:
        from weaviate import (  # noqa: F401
            Collection,
            AuthClientCredentials,
            AuthClientPassword,
            AuthBearerToken,
            AuthApiKey,
            BackupStorage,
            UnexpectedStatusCodeException,
            ObjectAlreadyExistsException,
            AuthenticationFailedException,
            SchemaValidationException,
            WeaviateStartUpError,
            ConsistencyLevel,
            WeaviateErrorRetryConf,
            EmbeddedOptions,
            AdditionalConfig,
            Config,
            ConnectionConfig,
            ConnectionParams,
            ProtocolParams,
            AdditionalProperties,
            LinkTo,
            Shard,
            Tenant,
            TenantActivityStatus,
        )
    assert len(recwarn) == 24


def test_nondeprecated_imports() -> None:
    with warnings.catch_warnings():
        from weaviate import (  # noqa: F401
            connect_to_custom,
            connect_to_embedded,
            connect_to_local,
            connect_to_wcs,
            collections,
            auth,
            backup,
            exceptions,
            data,
            batch,
            embedded,
            config,
            connect,
            gql,
            outputs,
            schema,
        )
