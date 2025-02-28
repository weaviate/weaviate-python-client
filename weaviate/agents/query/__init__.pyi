from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.query import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
