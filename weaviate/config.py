from dataclasses import dataclass, field
from typing import Optional


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
    connection_config: ConnectionConfig = field(default_factory=ConnectionConfig)

    def __post_init__(self) -> None:
        if self.grpc_port_experimental is not None and not isinstance(
            self.grpc_port_experimental, int
        ):
            raise TypeError(
                f"grpc_port_experimental must be {int}, received {type(self.grpc_port_experimental)}"
            )
