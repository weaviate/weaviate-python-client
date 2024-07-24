import os
from logging import getLogger

logger = getLogger("weaviate-client")
logger.setLevel(os.getenv("WEAVIATE_LOG_LEVEL", "INFO"))
