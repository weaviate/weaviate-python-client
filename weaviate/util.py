import validators

def generate_local_things_beacon(to_thing_uuid):
    """ Generates a beacon to the given thing.
        This may be helpful when adding cross references to objects.

    :param to_thing_uuid: The uuid of the object that will be referenced
    :type to_thing_uuid: str
    :return: the beacon in form of a dict
    :raises: ValueError, TypeError
    """
    if not isinstance(to_thing_uuid, str):
        raise TypeError("Expected to_thing_uuid of type str")
    if not validators.uuid(to_thing_uuid):
        raise ValueError("Uuid does not have the propper form")

    return {"beacon": "weaviate://localhost/things/" + to_thing_uuid}
