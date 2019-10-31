import validators
import requests
import json
import os


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

def _get_dict_from_object(object_):
    """ Takes an object that should describe a dict
    e.g. a schema or a thing and tries to retrieve the dict.
    Object m

    :param object_: May describe a dict in form of a json in form of an URL, File or python native dict
    :type object_: string, dict
    :return: dict
    :raises
        TypeError: if neither a string nor a dict
        ValueError: if no dict can be retrieved from object
    """

    # check if things files is url
    if object_ is None:
        raise TypeError("argument is None")

    if isinstance(object_, dict):
        # Object is already a dict
        return object_
    elif isinstance(object_, str):

        if validators.url(object_):
            # Object is URL
            f = requests.get(object_)
            if f.status_code == 200:
                return f.json()
            else:
                raise ValueError("Could not download file " + object_)

        elif not os.path.isfile(object_):
            # Object is neither file nor URL
            raise ValueError("No file found at location " + object_)
        else:
            # Object is file
            try:
                with open(object_, 'r') as file:
                    return json.load(file)
            except IOError:
                raise
    else:
        raise TypeError(
            "Argument is not of the supported types. Supported types are url or file path as string or schema as dict.")

