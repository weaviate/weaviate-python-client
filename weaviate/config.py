from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    session_pool_connections: int = Field(default=20)
    session_pool_maxsize: int = Field(default=20)


class Config(BaseModel):
    connection_config: ConnectionConfig = Field(default_factory=ConnectionConfig)
