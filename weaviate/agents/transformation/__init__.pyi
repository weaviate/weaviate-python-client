from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.transformation import *  # noqa: F403
except ImportError:
    raise WeaviateAgentsNotInstalledError
