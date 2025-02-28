from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.errors import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
