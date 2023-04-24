from dataclasses import dataclass, field


@dataclass
class SetupOptions:
    grpc_port_experimental: int = None


@dataclass
class Options:
    setup: SetupOptions = field(default_factory=SetupOptions)
