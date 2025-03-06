from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.transformation import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
