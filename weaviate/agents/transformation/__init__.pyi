from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.transformation import *  # type: ignore[import-not-found]
except ImportError:
    raise WeaviateAgentsNotInstalledError
