from typing import Optional
from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    session_pool_connections: int = Field(default=20)
    session_pool_maxsize: int = Field(default=20)


class Config(BaseModel):
    grpc_port_experimental: Optional[int] = Field(default=None)
    connection_config: ConnectionConfig = Field(default_factory=ConnectionConfig)
