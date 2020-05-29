from .batcher import Batcher
import uuid


def generate_uuid(identifier, namespace=""):
    """ Generate a uuid, may be used to consistently generate
    the same UUID for a specific identifier and namespace

    :param identifier: that should be used as basis for the uuid
    :param namespace: allows to namespace the identifier
    :return: uuid
    :rtype: str
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(namespace) + str(identifier)))

