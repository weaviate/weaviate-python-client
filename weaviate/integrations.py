from weaviate.connect.integrations import _IntegrationConfig
from weaviate.connect.v4 import Connection


class _Integrations:
    def __init__(self, connection: Connection) -> None:
        self.__connection = connection

    def configure(self, integrations_config: _IntegrationConfig | list[_IntegrationConfig]) -> None:
        if isinstance(integrations_config, _IntegrationConfig):
            integrations_config = [integrations_config]
        self.__connection.set_integrations(integrations_config)
        self.__connection._prepare_grpc_headers()
