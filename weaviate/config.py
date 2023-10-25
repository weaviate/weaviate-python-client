from dataclasses import dataclass, field
from typing import Optional, Tuple, Union

from pydantic import BaseModel, Field


@dataclass
class ConnectionConfig:
    session_pool_connections: int = 20
    session_pool_maxsize: int = 20

    def __post_init__(self) -> None:
        if not isinstance(self.session_pool_connections, int):
            raise TypeError(
                f"session_pool_connections must be {int}, received {type(self.session_pool_connections)}"
            )
        if not isinstance(self.session_pool_maxsize, int):
            raise TypeError(
                f"session_pool_maxsize must be {int}, received {type(self.session_pool_maxsize)}"
            )


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


class AdditionalConfig(BaseModel):
    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    proxies: Union[dict, str, None] = Field(default=None)
    startup_period: int = Field(default=5)
    timeout: Tuple[int, int] = Field(default_factory=lambda: (10, 60))
    trust_env: bool = Field(default=False)
