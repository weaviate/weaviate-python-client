from dataclasses import dataclass, field
from typing import Optional, Tuple, Union

from pydantic import BaseModel, Field


@dataclass
class ConnectionConfig:
    session_pool_connections: int = 20
    session_pool_maxsize: int = 100
    session_pool_max_retries: int = 3
    session_pool_timeout: int = 5

    def __post_init__(self) -> None:
        if not isinstance(self.session_pool_connections, int):
            raise TypeError(
                f"session_pool_connections must be {int}, received {type(self.session_pool_connections)}"
            )
        if not isinstance(self.session_pool_maxsize, int):
            raise TypeError(
                f"session_pool_maxsize must be {int}, received {type(self.session_pool_maxsize)}"
            )
        if not isinstance(self.session_pool_max_retries, int):
            raise TypeError(
                f"session_pool_max_retries must be {int}, received {type(self.session_pool_max_retries)}"
            )
        if not isinstance(self.session_pool_timeout, int):
            raise TypeError(
                f"session_pool_timeout must be {int}, received {type(self.session_pool_timeout)}"
            )


# used in v3 only
@dataclass
class Config:
    grpc_port_experimental: Optional[int] = None
    grpc_secure_experimental: bool = False
    connection_config: ConnectionConfig = field(default_factory=ConnectionConfig)

    def __post_init__(self) -> None:
        if self.grpc_port_experimental is not None and not isinstance(
            self.grpc_port_experimental, int
        ):
            raise TypeError(
                f"grpc_port_experimental must be {int}, received {type(self.grpc_port_experimental)}"
            )
        if not isinstance(self.grpc_secure_experimental, bool):
            raise TypeError(
                f"grpc_secure_experimental must be {bool}, received {type(self.grpc_secure_experimental)}"
            )


class Timeout(BaseModel):
    """Timeouts for the different operations in the client."""

    query: Union[int, float] = Field(default=30, ge=0)
    insert: Union[int, float] = Field(default=90, ge=0)
    init: Union[int, float] = Field(default=2, ge=0)


class Proxies(BaseModel):
    """Proxy configurations for sending requests to Weaviate through a proxy."""

    http: Optional[str] = Field(default=None)
    https: Optional[str] = Field(default=None)
    grpc: Optional[str] = Field(default=None)


class AdditionalConfig(BaseModel):
    """Use this class to specify the connection and proxy settings for your client when connecting to Weaviate.

    When specifying the timeout, you can either provide a tuple with the query and insert timeouts, or a `Timeout` object.
    The `Timeout` object gives you additional option to configure the `init` timeout, which controls how long the client
    initialisation checks will wait for before throwing. This is useful when you have a slow network connection.

    When specifying the proxies, be aware that supplying a URL (`str`) will populate all of the `http`, `https`, and grpc proxies.
    In order for this to be possible, you must have a proxy that is capable of handling simultaneous HTTP/1.1 and HTTP/2 traffic.
    """

    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    proxies: Union[str, Proxies, None] = Field(default=None)
    timeout_: Union[Tuple[int, int], Timeout] = Field(default_factory=Timeout, alias="timeout")
    trust_env: bool = Field(default=False)

    @property
    def timeout(self) -> Timeout:
        if isinstance(self.timeout_, tuple):
            return Timeout(query=self.timeout_[0], insert=self.timeout_[1])
        return self.timeout_
