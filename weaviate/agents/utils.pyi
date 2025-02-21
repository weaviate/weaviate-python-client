from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.utils import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
