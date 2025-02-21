from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.classes import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
