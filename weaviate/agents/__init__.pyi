from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
