from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.base import *  # type: ignore[import-not-found]
except ImportError:
    raise WeaviateAgentsNotInstalledError
