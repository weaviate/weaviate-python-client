from weaviate.connect import ConnectionV4


class _ClusterBase:
    def __init__(self, connection: ConnectionV4):
        self._connection = connection
