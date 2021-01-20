import json
import os
from typing import Union, Optional
import validators
import requests


def generate_local_beacon(to_uuid: str) -> dict:
    """
    Generates a beacon with the given uuid.

    Parameters
    ----------
    to_uuid : str
        The UUID for which to create a local beacon.

    Returns
    -------
    dict
        The local beacon.

    Raises
    ------
    TypeError
        If 'to_uuid' is not of type str.
    ValueError
        If the 'to_uuid' is not valid.
    """

    if not isinstance(to_uuid, str):
        raise TypeError("Expected to_object_uuid of type str")
    if not validators.uuid(to_uuid):
        raise ValueError("Uuid does not have the propper form")
    return {"beacon": "weaviate://localhost/" + to_uuid}


def _get_dict_from_object(object_: Union[str, dict]) -> dict:
    """
    Takes an object that should describe a dict
    e.g. a schema or a object and tries to retrieve the dict.

    Parameters
    ----------
    object_ : str or dict
        The object from which to retrieve the dict.
        Can be a python dict, or the path to a json file or a url of a json file.

    Returns
    -------
    dict
        The object as a dict.

    Raises
    ------
    TypeError
        If neither a string nor a dict.
    ValueError
        If no dict can be retrieved from object.
    """

    # check if objects files is url
    if object_ is None:
        raise TypeError("argument is None")

    if isinstance(object_, dict):
        # Object is already a dict
        return object_
    if isinstance(object_, str):
        if validators.url(object_):
            # Object is URL
            response = requests.get(object_)
            if response.status_code == 200:
                return response.json()
            raise ValueError("Could not download file " + object_)

        if not os.path.isfile(object_):
            # Object is neither file nor URL
            raise ValueError("No file found at location " + object_)
        # Object is file
        with open(object_, 'r') as file:
            return json.load(file)
    raise TypeError("Argument is not of the supported types. Supported types are \
                                    url or file path as string or schema as dict.")


def is_weaviate_object_url(url: str) -> bool:
    """
    Checks if the input follows a normal url like this:
    'weaviate://localhost/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'

    Parameters
    ----------
    input : str
        The URL to be validated.

    Returns
    -------
    bool
        True if 'input' is an weaviate object URL.
        False otherwise.
    """

    if not isinstance(url, str):
        return False
    if not url.startswith("weaviate://"):
        return False
    url = url[11:]
    split = url.split("/")
    if len(split) != 2:
        return False
    if split[0] != "localhost":
        if not validators.domain(split[0]):
            return False
    if not validators.uuid(split[1]):
        return False
    return True


def is_object_url(url: str) -> bool:
    """
    Validates if an url like http://localhost:8080/v1/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446
    references a object. It only validates the path not the host or the protocol.

    Parameters
    ----------
    input : str
        The URL to be validated.

    Returns
    -------
    bool
        True if the 'input' is a valid path to an object.
        False otherwise.
    """

    split = url.split("/")
    if len(split) < 3:
        return False
    if not validators.uuid(split[-1]):
        return False
    if not split[-2] == "objects":
        return False
    if not split[-3] == "v1":
        return False
    return True


def get_valid_uuid(uuid: str) -> Optional[str]:
    """
    Validate the UUID.

    Parameters
    ----------
    uuid : str
        The UUID to be validated.
        Should be in the form of an UUID or in form of an URL.
        E.g.
        'http://localhost:8080/v1/objects/fc7eb129-f138-457f-b727-1b29db191a67'
        or
        'fc7eb129-f138-457f-b727-1b29db191a67'

    Returns
    -------
    str or None
        If the 'uuid' is not valid it returns None,
        otherwise it returns the extracted.

    Raises
    ------
    TypeError
        If 'uuid' is not of type str.
    """

    if not isinstance(uuid, str):
        raise TypeError("uuid must be of type str but was: " + str(type(uuid)))

    _is_weaviate_url = is_weaviate_object_url(uuid)
    _is_object_url = is_object_url(uuid)
    _uuid = uuid
    if _is_weaviate_url or _is_object_url:
        _uuid = uuid.split("/")[-1]
    if not validators.uuid(_uuid):
        return None
    return _uuid


def get_uuid_from_weaviate_url(url: str) -> str:
    """
    Get the UUID from a weaviate URL.

    Parameters
    ----------
    url : str
        The weaviate URL.
        Of this form: 'weaviate://localhost/objects/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'

    Returns
    -------
    str
        The UUID.
    """

    return url.split("/")[-1]


def get_domain_from_weaviate_url(url: str) -> str:
    """
    Get the domain from a weaviate URL.

    Parameters
    ----------
    url : str
        The weaviate URL.
        Of this form: 'weaviate://localhost/objects/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'

    Returns
    -------
    str
        The domain.
    """

    return url[11:].split("/")[0]


def _is_sub_schema(sub_schema: dict, schema: dict) -> bool:
    """
    Check for a subset in a schema.

    Parameters
    ----------
    sub_schema : dict
        The smaller schema that should be contained in the 'schema'.
    schema : dict
        The schema for which to check if 'sub_schema' is a part of.

    Returns
    -------
    bool
        True is 'sub_schema' is a subset of the 'schema'.
        False otherwise.
    """

    schema_classes = schema.get("classes", [])
    sub_schema_classes = sub_schema.get("classes", [])
    return _compare_class_sets(sub_schema_classes, schema_classes)


def _compare_class_sets(sub_set: list, set_: list) -> bool:
    """
    Check for a subset in a set of classes.

    Parameters
    ----------
    sub_set : list
        The smaller set that should be contained in the 'set'.
    schema : dict
        The set for which to check if 'sub_set' is a part of.

    Returns
    -------
    bool
        True is 'sub_set' is a subset of the 'set'.
        False otherwise.
    """

    for sub_set_class in sub_set:
        found = False
        for set_class in set_:
            if sub_set_class["class"] == set_class["class"]:
                if _compare_properties(sub_set_class["properties"], set_class["properties"]):
                    found = True
                    break
        if not found:
            return False
    return True


def _compare_properties(sub_set: list, set_: list) -> bool:
    """
    Check for a subset in a set of properties.

    Parameters
    ----------
    sub_set : list
        The smaller set that should be contained in the 'set'.
    schema : dict
        The set for which to check if 'sub_set' is a part of.

    Returns
    -------
    bool
        True is 'sub_set' is a subset of the 'set'.
        False otherwise.
    """

    for sub_set_property in sub_set:
        found = False
        for set_property in set_:
            if sub_set_property["name"] == set_property["name"]:
                found = True
                break
        if not found:
            return False
    return True
