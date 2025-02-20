from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.utils import *  # type: ignore
except ImportError:
    raise WeaviateAgentsNotInstalledError
