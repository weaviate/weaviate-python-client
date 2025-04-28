from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents.utils import *  # noqa: F403
except ImportError:
    raise WeaviateAgentsNotInstalledError
