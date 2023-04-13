from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConnectionConfiguration:
    session_pool_connections: int = 20
    session_pool_maxsize: int = 20

    def __post_init__(self):
        if not isinstance(self.session_pool_connections, int):
            raise TypeError(
                f"grpc_port_experimental must be {int}, received {type(self.session_pool_connections)}"
            )
        if not isinstance(self.session_pool_maxsize, int):
            raise TypeError(
                f"grpc_port_experimental must be {int}, received {type(self.session_pool_maxsize)}"
            )


@dataclass
class Configuration:
    grpc_port_experimental: Optional[int] = None
    connection_config: ConnectionConfiguration = field(default_factory=ConnectionConfiguration)

    def __post_init__(self):
        if self.grpc_port_experimental is not None and not isinstance(
            self.grpc_port_experimental, int
        ):
            raise TypeError(
                f"grpc_port_experimental must be {int}, received {type(self.grpc_port_experimental)}"
            )
