from dataclasses import dataclass


@dataclass
class Configuration:
    grpc_port_experimental: int = None

    def __post_init__(self):
        if not isinstance(self.grpc_port_experimental, int):
            raise TypeError(
                f"grpc_port_experimental must be an integer, received {type(self.grpc_port_experimental)}"
            )
