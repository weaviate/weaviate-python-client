from weaviate.cluster.replicate.executor import _ReplicateExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("sync")
class _Replicate(_ReplicateExecutor[ConnectionAsync]):
    pass
