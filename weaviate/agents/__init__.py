from weaviate.exceptions import WeaviateAgentsNotInstalledError

try:
    from weaviate_agents import *  # type: ignore # noqa: F403, F401
except ImportError:
    raise WeaviateAgentsNotInstalledError
