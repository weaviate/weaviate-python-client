from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.personalization import *
except ImportError:
    raise WeaviateAgentsNotInstalledError
