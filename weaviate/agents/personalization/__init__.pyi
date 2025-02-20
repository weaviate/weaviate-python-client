from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.personalization import *  # type: ignore
except ImportError:
    raise WeaviateAgentsNotInstalledError
