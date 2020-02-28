from .client import Client
from .batch import ReferenceBatchRequest
from .batch import ThingsBatchRequest
from .exceptions import *
from .util import generate_local_things_beacon
from .classify import SOURCE_WHERE_FILTER, TRAINING_SET_WHERE_FILTER, TARGET_WHERE_FILTER
from .auth import AuthClientCredentials, AuthClientPassword
from .client_config import ClientConfig

name = "weaviate"

