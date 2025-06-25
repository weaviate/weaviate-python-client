from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.personalization import *  # noqa: F403
except ImportError:
    raise WeaviateAgentsNotInstalledError
