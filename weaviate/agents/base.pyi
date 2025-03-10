from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.base import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
