"""
Helper functions!
"""
import os
import json
import base64
import uuid as uuid_lib
from typing import Union, Sequence, Tuple, Any
from numbers import Real
from io import BufferedReader
import validators
import requests

from weaviate.exceptions import SchemaValidationException


def image_encoder_b64(image_or_image_path: Union[str, BufferedReader]) -> str:
    """
    Encode a image in a Weaviate understandable format from a binary read file or by providing
    the image path.

    Parameters
    ----------
    image_or_image_path : str, io.BufferedReader
        The binary read file or the path to the file.

    Returns
    -------
    str
        Encoded image.

    Raises
    ------
    ValueError
        If the argument is str and does not point to an existing file.
    TypeError
        If the argument is of a wrong data type.
    """


    if isinstance(image_or_image_path, str):
        if not os.path.isfile(image_or_image_path):
            raise ValueError("No file found at location " + image_or_image_path)
        with open(image_or_image_path, 'br') as file:
            content = file.read()

    elif isinstance(image_or_image_path, BufferedReader):
        content = image_or_image_path.read()
    else:
        raise TypeError('"image_or_image_path" should be a image path or a binary read file'
            ' (io.BufferedReader)')
    return base64.b64encode(content).decode("utf-8")


def image_decoder_b64(encoded_image: str) -> bytes:
    """
    Decode image from a Weaviate format image.

    Parameters
    ----------
    encoded_image : str
        The encoded image.

    Returns
    -------
    bytes
        Decoded image as a binary string.
    """

    return base64.b64decode(encoded_image.encode('utf-8'))


def generate_local_beacon(to_uuid: Union[str, uuid_lib.UUID]) -> dict:
    """
    Generates a beacon with the given uuid.

    Parameters
    ----------
    to_uuid : str or uuid.UUID
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


    if isinstance(to_uuid, str):
        try:
            uuid = str(uuid_lib.UUID(to_uuid))
        except ValueError:
            raise ValueError("Uuid does not have the propper form") from None
    elif isinstance(to_uuid, uuid_lib.UUID):
        uuid = str(to_uuid)
    else:
        raise TypeError("Expected to_object_uuid of type str or uuid.UUID")
    
    return {"beacon": "weaviate://localhost/" + uuid}


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
        If 'object_' is neither a string nor a dict.
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
    raise TypeError("Argument is not of the supported types. Supported types are "
                    "url or file path as string or schema as dict.")


def is_weaviate_object_url(url: str) -> bool:
    """
    Checks if the input follows a normal Weaviate 'beacon' like this:
    'weaviate://localhost/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'

    Parameters
    ----------
    input : str
        The URL to be validated.

    Returns
    -------
    bool
        True if 'input' is a Weaviate object URL.
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
    try:
        uuid_lib.UUID(split[1])
    except ValueError:
        return False
    return True


def is_object_url(url: str) -> bool:
    """
    Validates an url like 'http://localhost:8080/v1/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446'
    or '/v1/objects/1c9cd584-88fe-5010-83d0-017cb3fcb446' references a object. It only validates
    the path format and UUID, not the host or the protocol.

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
    try:
        uuid_lib.UUID(split[-1])
    except ValueError:
        return False
    if not split[-2] == "objects":
        return False
    if not split[-3] == "v1":
        return False
    return True


def get_valid_uuid(uuid: Union[str, uuid_lib.UUID]) -> str:
    """
    Validate and extract the UUID.

    Parameters
    ----------
    uuid : str or uuid.UUID
        The UUID to be validated and extracted.
        Should be in the form of an UUID or in form of an URL (weaviate 'beacon' or 'href').
        E.g.
        'http://localhost:8080/v1/objects/fc7eb129-f138-457f-b727-1b29db191a67'
        or
        'weaviate://localhost/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'
        or
        'fc7eb129-f138-457f-b727-1b29db191a67'

    Returns
    -------
    str
        The extracted UUID.

    Raises
    ------
    TypeError
        If 'uuid' is not of type str.
    ValueError
        If 'uuid' is not valid or cannot be extracted.
    """

    if isinstance(uuid, uuid_lib.UUID):
        return str(uuid)

    if not isinstance(uuid, str):
        raise TypeError("'uuid' must be of type str or uuid.UUID, but was: " + str(type(uuid)))

    _is_weaviate_url = is_weaviate_object_url(uuid)
    _is_object_url = is_object_url(uuid)
    _uuid = uuid
    if _is_weaviate_url or _is_object_url:
        _uuid = uuid.split("/")[-1]
    try:
        _uuid = str(uuid_lib.UUID(_uuid))
    except ValueError:
        raise ValueError("Not valid 'uuid' or 'uuid' can not be extracted from value") from None
    return _uuid


def get_vector(vector: Sequence) -> list:
    """
    Get weaviate compatible format of the embedding vector.

    Parameters
    ----------
    vector: Sequence
        The embedding of an object. Used only for class objects that do not have a vectorization
        module. Supported types are `list`, `numpy.ndarray`, `torch.Tensor` and `tf.Tensor`.

    Returns
    -------
    list
        The embedding as a list.

    Raises
    ------
    TypeError
        If 'vector' is not of a supported type.
    """

    if isinstance(vector, list):
        # if vector is already a list
        return vector
    try:
        # if vetcor is numpy.ndarray or torch.Tensor
        return vector.squeeze().tolist()
    except AttributeError:
        try:
            # if vector is tf.Tensor
            return vector.numpy().squeeze().tolist()
        except AttributeError:
            raise TypeError("The type of the 'vector' argument is not supported!\n"
                "Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` "
                "and `tf.Tensor`") from None


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
        The schema for which to check if 'sub_schema' is a part of. Must have the 'classes' key.

    Returns
    -------
    bool
        True is 'sub_schema' is a subset of the 'schema'.
        False otherwise.
    """

    schema_classes = schema.get("classes", [])
    if 'classes' in sub_schema:
        sub_schema_classes = sub_schema["classes"]
    else:
        sub_schema_classes = [sub_schema]
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
            if 'class' not in sub_set_class:
                raise SchemaValidationException(
                    "The sub schema class/es MUST have a 'class' keyword each!"
                )
            if (
                _capitalize_first_letter(sub_set_class["class"]) == \
                _capitalize_first_letter(set_class["class"])
            ):
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


def _get_valid_timeout_config(timeout_config: Union[Tuple[Real, Real], Real, None]):
    """
    Validate and return TimeOut configuration.

    Parameters
    ----------
    timeout_config : tuple(Real, Real) or Real or None, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            real number or, a tuple of two real numbers: (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value.

    Raises
    ------
    TypeError
        If arguments are of a wrong data type.
    ValueError
        If 'timeout_config' is not a tuple of 2.
    ValueError
        If 'timeout_config' is/contains negative number/s.
    """


    if isinstance(timeout_config, Real) and not isinstance(timeout_config, bool):
        if timeout_config <= 0.0:
            raise ValueError("'timeout_config' cannot be non-positive number/s!")
        return (timeout_config, timeout_config)

    if not isinstance(timeout_config, tuple):
        raise TypeError("'timeout_config' should be a (or tuple of) positive real number/s!")
    if len(timeout_config) != 2:
        raise ValueError("'timeout_config' must be of length 2!")
    if not (isinstance(timeout_config[0], Real) and isinstance(timeout_config[1], Real)) or\
        (isinstance(timeout_config[0], bool) and isinstance(timeout_config[1], bool)):
        raise TypeError("'timeout_config' must be tuple of real numbers")
    if timeout_config[0] <= 0.0 or timeout_config[1] <= 0.0:
        raise ValueError("'timeout_config' cannot be non-positive number/s!")
    return timeout_config

def generate_uuid5(identifier: Any, namespace: Any = "") -> str:
    """
    Generate an UUIDv5, may be used to consistently generate the same UUID for a specific
    identifier and namespace.

    Parameters
    ----------
    identifier : Any
        The identifier/object that should be used as basis for the UUID.
    namespace : Any, optional
        Allows to namespace the identifier, by default ""

    Returns
    -------
    str
        The UUID as a string.
    """

    return str(uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, str(namespace) + str(identifier)))


def _capitalize_first_letter(string: str) -> str:
    """
    Capitalize only the first letter of the `string`.

    Parameters
    ----------
    string : str
        The string to be capitalized.

    Returns
    -------
    str
        The capitalized string.
    """

    if len(string) == 1:
        return string.capitalize()
    return string[0].capitalize() + string[1:]
