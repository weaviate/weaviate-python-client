from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents import *  # noqa: F403
except ImportError:
    raise WeaviateAgentsNotInstalledError
