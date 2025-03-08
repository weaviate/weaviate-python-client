from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.personalization import *  # type: ignore[import-not-found]
except ImportError:
    raise WeaviateAgentsNotInstalledError
