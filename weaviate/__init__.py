SEMANTIC_TYPE_THINGS = "things"
SEMANTIC_TYPE_ACTIONS = "actions"

from .client import Client
from .batch import ReferenceBatchRequest
from .batch import ThingsBatchRequest
from .batch import ActionsBatchRequest
from .exceptions import *
from .util import generate_local_beacon
from .classification import SOURCE_WHERE_FILTER, TRAINING_SET_WHERE_FILTER, TARGET_WHERE_FILTER
from .auth import AuthClientCredentials, AuthClientPassword
from .client_config import ClientConfig


name = "weaviate"

