"""
Client class definition.
"""

import asyncio
from typing import Optional, Tuple, Union, Any

from typing_extensions import deprecated

from weaviate import syncify
from weaviate.backup.backup import _BackupAsync
from weaviate.backup.sync import _Backup
from weaviate.event_loop import _EventLoopSingleton, _EventLoop

from weaviate.users.users import _UsersAsync

from weaviate.users.sync import _Users
from .auth import AuthCredentials
from .client_base import _WeaviateClientBase
from .collections.batch.client import _BatchClientWrapper
from .collections.cluster import _Cluster, _ClusterAsync
from .collections.collections.async_ import _CollectionsAsync
from .collections.collections.sync import _Collections
from .config import AdditionalConfig
from .connect.base import (
    ConnectionParams,
)
from .debug import _Debug, _DebugAsync
from .embedded import EmbeddedOptions
from .rbac import _RolesAsync, _Roles
from .types import NUMBER

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]


@syncify.convert
class WeaviateClient(_WeaviateClientBase):
    """
    The v4 Python-native Weaviate Client class that encapsulates Weaviate functionalities in one object.

    WARNING: This client is only compatible with Weaviate v1.23.6 and higher!

    A Client instance creates all the needed objects to interact with Weaviate, and connects all of
    them to the same Weaviate instance. See below the Attributes of the Client instance. For the
    per attribute functionality see that attribute's documentation.

    Attributes:
        `backup`
            A `Backup` object instance connected to the same Weaviate instance as the Client.
        `batch`
            A `_Batch` object instance connected to the same Weaviate instance as the Client.
        `classification`
            A `Classification` object instance connected to the same Weaviate instance as the Client.
        `cluster`
            A `Cluster` object instance connected to the same Weaviate instance as the Client.
        `collections`
            A `_Collections` object instance connected to the same Weaviate instance as the Client.
    """

    def __init__(
        self,
        connection_params: Optional[ConnectionParams] = None,
        embedded_options: Optional[EmbeddedOptions] = None,
        auth_client_secret: Optional[AuthCredentials] = None,
        additional_headers: Optional[dict] = None,
        additional_config: Optional[AdditionalConfig] = None,
        skip_init_checks: bool = False,
    ) -> None:
        self._event_loop = _EventLoopSingleton.get_instance()
        assert self._event_loop.loop is not None
        self._loop = self._event_loop.loop

        super().__init__(
            connection_params=connection_params,
            embedded_options=embedded_options,
            auth_client_secret=auth_client_secret,
            additional_headers=additional_headers,
            additional_config=additional_config,
            skip_init_checks=skip_init_checks,
        )

        collections = _Collections(self._event_loop, _CollectionsAsync(self._connection))

        self.batch = _BatchClientWrapper(self._connection, config=collections)
        """This namespace contains all the functionality to upload data in batches to Weaviate for all collections and tenants."""
        self.backup = _Backup(self._connection)
        """This namespace contains all functionality to backup data."""
        self.cluster = _Cluster(self._connection)
        """This namespace contains all functionality to inspect the connected Weaviate cluster."""
        self.collections = collections
        """This namespace contains all the functionality to manage Weaviate data collections. It is your main entry point for all collection-related functionality.

        Use it to retrieve collection objects using `client.collections.use("MyCollection")` or to create new collections using `client.collections.create("MyCollection", ...)`.
        """
        self.debug = _Debug(self._connection)
        """This namespace contains functionality used to debug Weaviate clusters. As such, it is deemed experimental and is subject to change.

        We can make no guarantees about the stability of this namespace nor the potential for future breaking changes. Use at your own risk."""
        self.roles = _Roles(self._connection)
        """This namespace contains all functionality to manage Weaviate's RBAC functionality."""

        self.users = _Users(self._connection)
        """This namespace contains all functionality to manage Weaviate users."""

    def __enter__(self) -> "WeaviateClient":
        self.connect()  # pyright: ignore # gets patched by syncify.convert to be sync
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()  # pyright: ignore # gets patched by syncify.convert to be sync


class WeaviateAsyncClient(_WeaviateClientBase):
    """
    The v4 Python-native Weaviate Client class that encapsulates Weaviate functionalities in one object.

    WARNING: This client is only compatible with Weaviate v1.23.6 and higher!

    A Client instance creates all the needed objects to interact with Weaviate, and connects all of
    them to the same Weaviate instance. See below the Attributes of the Client instance. For the
    per attribute functionality see that attribute's documentation.

    Attributes:
        `backup`
            A `Backup` object instance connected to the same Weaviate instance as the Client.
        `cluster`
            A `Cluster` object instance connected to the same Weaviate instance as the Client.
        `collections`
            A `_CollectionsAsync` object instance connected to the same Weaviate instance as the Client.
    """

    def __init__(
        self,
        connection_params: Optional[ConnectionParams] = None,
        embedded_options: Optional[EmbeddedOptions] = None,
        auth_client_secret: Optional[AuthCredentials] = None,
        additional_headers: Optional[dict] = None,
        additional_config: Optional[AdditionalConfig] = None,
        skip_init_checks: bool = False,
    ) -> None:
        self._loop = asyncio.get_event_loop()
        _EventLoop.patch_exception_handler(self._loop)

        super().__init__(
            connection_params=connection_params,
            embedded_options=embedded_options,
            auth_client_secret=auth_client_secret,
            additional_headers=additional_headers,
            additional_config=additional_config,
            skip_init_checks=skip_init_checks,
        )

        self.backup = _BackupAsync(self._connection)
        """This namespace contains all functionality to backup data."""
        self.cluster = _ClusterAsync(self._connection)
        """This namespace contains all functionality to inspect the connected Weaviate cluster."""
        self.collections = _CollectionsAsync(self._connection)
        """This namespace contains all the functionality to manage Weaviate data collections. It is your main entry point for all collection-related functionality.

        Use it to retrieve collection objects using `client.collections.use("MyCollection")` or to create new collections using `await client.collections.create("MyCollection", ...)`.
        """
        self.debug = _DebugAsync(self._connection)
        """This namespace contains functionality used to debug Weaviate clusters. As such, it is deemed experimental and is subject to change.

        We can make no guarantees about the stability of this namespace nor the potential for future breaking changes. Use at your own risk."""
        self.roles = _RolesAsync(self._connection)
        """This namespace contains all functionality to manage Weaviate's RBAC functionality."""

        self.users = _UsersAsync(self._connection)
        """This namespace contains all functionality to manage Weaviate users."""

    async def __aenter__(self) -> "WeaviateAsyncClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.close()


@deprecated(
    """
Python client v3 `weaviate.Client(...)` has been removed.

Upgrade your code to use Python client v4 `weaviate.WeaviateClient` connections and methods.
    - For Python Client v4 usage, see: https://weaviate.io/developers/weaviate/client-libraries/python
    - For code migration, see: https://weaviate.io/developers/weaviate/client-libraries/python/v3_v4_migration

If you have to use v3 code, install the v3 client and pin the v3 dependency in your requirements file: `weaviate-client>=3.26.7;<4.0.0`"""
)
class Client:

    def __init__(
        self,
    ) -> None:
        raise ValueError(
            """
Python client v3 `weaviate.Client(...)` has been removed.

Upgrade your code to use Python client v4 `weaviate.WeaviateClient` connections and methods.
    - For Python Client v4 usage, see: https://weaviate.io/developers/weaviate/client-libraries/python
    - For code migration, see: https://weaviate.io/developers/weaviate/client-libraries/python/v3_v4_migration

If you have to use v3 code, install the v3 client and pin the v3 dependency in your requirements file: `weaviate-client>=3.26.7;<4.0.0`"""
        )
