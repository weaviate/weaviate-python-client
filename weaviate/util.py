"""
Helper functions!
"""

import base64
import datetime
import io
import os
import re
import uuid as uuid_lib
from pathlib import Path
from typing import Union, Sequence, Any, Optional, List, Dict, Generator, Tuple, cast

import httpx
import validators

from weaviate.exceptions import (
    SchemaValidationError,
    UnexpectedStatusCodeError,
    ResponseCannotBeDecodedError,
    WeaviateInvalidInputError,
    WeaviateUnsupportedFeatureError,
)
from weaviate.types import NUMBER, UUIDS, TIME
from weaviate.validator import _is_valid, _ExtraTypes
from weaviate.warnings import _Warnings

PYPI_PACKAGE_URL = "https://pypi.org/pypi/weaviate-client/json"
MAXIMUM_MINOR_VERSION_DELTA = 3  # The maximum delta between minor versions of Weaviate Client that will not trigger an upgrade warning.
MINIMUM_NO_WARNING_VERSION = (
    "v1.16.0"  # The minimum version of Weaviate that will not trigger an upgrade warning.
)
BYTES_PER_CHUNK = 65535  # The number of bytes to read per chunk when encoding files ~ 64kb


def image_encoder_b64(image_or_image_path: Union[str, io.BufferedReader]) -> str:
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
        with open(image_or_image_path, "br") as file:
            content = file.read()

    elif isinstance(image_or_image_path, io.BufferedReader):
        content = image_or_image_path.read()
    else:
        raise TypeError(
            '"image_or_image_path" should be a image path or a binary read file'
            " (io.BufferedReader)"
        )
    return base64.b64encode(content).decode("utf-8")


def file_encoder_b64(file_or_file_path: Union[str, Path, io.BufferedReader]) -> str:
    """
    Encode a file in a Weaviate understandable format from an io.BufferedReader binary read file or by providing
    the file path as either a string of a pathlib.Path object

    If you pass an io.BufferedReader object, it is your responsibility to close it after encoding.

    Parameters
    ----------
    file_or_file_path : str, pathlib.Path io.BufferedReader
        The binary read file or the path to the file.

    Returns
    -------
    str
        Encoded file.

    Raises
    ------
    ValueError
        If the argument is str and does not point to an existing file.
    TypeError
        If the argument is of a wrong data type.
    """

    def _chunks(buffer: io.BufferedReader, chunk_size: int) -> Generator[bytes, Any, Any]:
        while True:
            data = buffer.read(chunk_size)
            if not data:
                break
            yield data

    should_close_file = False
    use_buffering = True
    file = None

    try:
        if isinstance(file_or_file_path, str):
            if not os.path.isfile(file_or_file_path):
                raise ValueError("No file found at location " + file_or_file_path)
            file = open(file_or_file_path, "br")
            should_close_file = True
            use_buffering = os.path.getsize(file_or_file_path) > BYTES_PER_CHUNK
        elif isinstance(file_or_file_path, Path):
            if not file_or_file_path.is_file():
                raise ValueError("No file found at location " + str(file_or_file_path))
            file = file_or_file_path.open("br")
            should_close_file = True
            use_buffering = file_or_file_path.stat().st_size > BYTES_PER_CHUNK
        elif isinstance(file_or_file_path, io.BufferedReader):
            file = file_or_file_path
        else:
            raise TypeError(
                '"file_or_file_path" should be a file path or a binary read file'
                " (io.BufferedReader)"
            )

        if use_buffering:
            encoded: str = ""
            for chunk in _chunks(file, BYTES_PER_CHUNK):
                encoded += base64.b64encode(chunk).decode("utf-8")
        else:
            encoded = base64.b64encode(file.read()).decode("utf-8")

    finally:
        if should_close_file and file is not None:
            file.close()

    return encoded


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

    return base64.b64decode(encoded_image.encode("utf-8"))


def file_decoder_b64(encoded_file: str) -> bytes:
    """
    Decode file from a Weaviate format image.

    Parameters
    ----------
    encoded_file : str
        The encoded file.

    Returns
    -------
    bytes
        Decoded file as a binary string. Use this in your file
        handling code to convert it into a specific file type of choice.
        E.g., PIL for images.
    """

    return base64.b64decode(encoded_file.encode("utf-8"))


def is_weaviate_object_url(url: str) -> bool:
    """
    Checks if the input follows a normal Weaviate 'beacon' like this:
    'weaviate://localhost/ClassName/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'

    Parameters
    ----------
    url : str
        The URL to be validated.

    Returns
    -------
    bool
        True if the 'url' is a Weaviate object URL.
        False otherwise.
    """

    if not isinstance(url, str):
        return False
    if not url.startswith("weaviate://"):
        return False
    url = url[11:]
    split = url.split("/")
    if len(split) not in (2, 3):
        return False
    if split[0] != "localhost":
        if not validators.domain(split[0]):
            return False
    try:
        uuid_lib.UUID(split[-1])
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
    url : str
        The URL to be validated.

    Returns
    -------
    bool
        True if the 'url' is a valid path to an object.
        False otherwise.
    """

    v1_split = url.split("/v1/")

    if len(v1_split) != 2:
        return False

    split = v1_split[1].split("/")

    if len(split) not in (2, 3):
        return False

    try:
        uuid_lib.UUID(split[-1])
    except ValueError:
        return False
    if not split[0] == "objects":
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


def get_vector(vector: Sequence) -> Sequence[float]:
    """
    Get weaviate compatible format of the embedding vector.

    Parameters
    ----------
    vector: Sequence
        The embedding of an object. Used only for class objects that do not have a vectorization
        module. Supported types are `list`, `numpy.ndarray`, `torch.Tensor`, `tf.Tensor`, `pd.Series` and `pl.Series`.

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
        # if vector is numpy.ndarray or torch.Tensor
        return vector.squeeze().tolist()  # type: ignore
    except AttributeError:
        pass
    try:
        # if vector is tf.Tensor or torch.Tensor
        return vector.numpy().squeeze().tolist()  # type: ignore
    except AttributeError:
        pass
    try:
        # if vector is pd.Series or pl.Series
        return vector.to_list()  # type: ignore
    except AttributeError:
        pass
    raise TypeError(
        "The type of the 'vector' argument is not supported!\n"
        "Supported types are `list`, 'numpy.ndarray`, `torch.Tensor`, `tf.Tensor`, `pd.Series`, and `pl.Series`"
    ) from None


def _get_vector_v4(vector: Any) -> Sequence[float]:
    try:
        return get_vector(vector)
    except TypeError as e:
        raise WeaviateInvalidInputError(
            f"The vector you supplied was malformatted! Vector:  {vector}"
        ) from e


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
    if "classes" in sub_schema:
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
    set_ : list
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
            if "class" not in sub_set_class:
                raise SchemaValidationError(
                    "The sub schema class/es MUST have a 'class' keyword each!"
                )
            if _capitalize_first_letter(sub_set_class["class"]) == _capitalize_first_letter(
                set_class["class"]
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
    set_ : list
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


def check_batch_result(
    results: Optional[List[Dict[str, Any]]],
) -> None:
    """
    Check batch results for errors.

    Parameters
    ----------
    results : dict
        The Weaviate batch creation return value.
    """

    if results is None:
        return
    for result in results:
        if "result" in result and "errors" in result["result"]:
            if "error" in result["result"]["errors"]:
                print(result["result"]["errors"])


def _check_positive_num(
    value: Any, arg_name: str, data_type: type, include_zero: bool = False
) -> None:
    """
    Check if the `value` of the `arg_name` is a positive number.

    Parameters
    ----------
    value : Union[int, float]
        The value to check.
    arg_name : str
        The name of the variable from the original function call. Used for error message.
    data_type : type
        The data type to check for.
    include_zero : bool
        Wether zero counts as positive or not. By default False.

    Raises
    ------
    TypeError
        If the `value` is not of type `data_type`.
    ValueError
        If the `value` has a non positive value.
    """

    if not isinstance(value, data_type) or isinstance(value, bool):
        raise TypeError(f"'{arg_name}' must be of type {data_type}.")
    if include_zero:
        if value < 0:  # type: ignore
            raise ValueError(f"'{arg_name}' must be positive, i.e. greater or equal to zero (>=0).")
    else:
        if value <= 0:  # type: ignore
            raise ValueError(f"'{arg_name}' must be positive, i.e. greater that zero (>0).")


def is_weaviate_domain(url: str) -> bool:
    return (
        "weaviate.io" in url.lower()
        or "semi.technology" in url.lower()
        or "weaviate.cloud" in url.lower()
    )


def strip_newlines(s: str) -> str:
    return s.replace("\n", " ")


def _sanitize_str(value: str) -> str:
    """
    Ensures string is sanitized for GraphQL.

    Parameters
    ----------
    value : str
        The value to be converted.

    Returns
    -------
    str
        The sanitized string.
    """
    value = strip_newlines(value)
    value = re.sub(
        r'(?<!\\)((?:\\{2})*)"', r"\1\"", value
    )  # only replaces unescaped double quotes without permitting query injection
    return f'"{value}"'


def parse_version_string(ver_str: str) -> tuple:
    """
    Parse a version string into a float.

    Parameters
    ----------
    ver_str : str
        The version string to parse. (e.g. "v1.18.2" or "1.18.0")

    Returns
    -------
    tuple :
        The parsed version as a tuple with len(2). (e.g. (1, 18)) Note: Ignores the patch version.
    """
    if ver_str.count(".") == 0:
        ver_str = ver_str + ".0"

    pattern = r"v?(\d+)\.(\d+)"
    match = re.match(pattern, ver_str)

    if match:
        ver_tup = tuple(map(int, match.groups()))
        return ver_tup
    else:
        raise ValueError(
            f"Unable to parse a version from the input string: {ver_str}. Is it in the format '(v)x.y.z' (e.g. 'v1.18.2' or '1.18.0')?"
        )


class _ServerVersion:
    def __init__(self, major: int, minor: int, patch: int) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ServerVersion):
            return NotImplemented
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __neq__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: "_ServerVersion") -> bool:
        if self.major > other.major:
            return True
        elif self.major == other.major:
            if self.minor > other.minor:
                return True
            elif self.minor == other.minor:
                if self.patch > other.patch:
                    return True
        return False

    def __lt__(self, other: "_ServerVersion") -> bool:
        return not self.__gt__(other) and not self.__eq__(other)

    def __ge__(self, other: "_ServerVersion") -> bool:
        return self.__gt__(other) or self.__eq__(other)

    def __le__(self, other: "_ServerVersion") -> bool:
        return self.__lt__(other) or self.__eq__(other)

    def __repr__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_at_least(self, major: int, minor: int, patch: int) -> bool:
        return self >= _ServerVersion(major, minor, patch)

    def is_lower_than(self, major: int, minor: int, patch: int) -> bool:
        return self < _ServerVersion(major, minor, patch)

    @classmethod
    def from_string(cls, version: str) -> "_ServerVersion":
        initial = version
        if version == "":
            version = "0"
        if version.count(".") == 0:
            version = version + ".0"
        if version.count(".") == 1:
            version = version + ".0"

        pattern = r"v?(\d+)\.(\d+)\.(\d+)"
        match = re.match(pattern, version)

        if match:
            ver_tup = tuple(map(int, match.groups()))
            return cls(major=ver_tup[0], minor=ver_tup[1], patch=ver_tup[2])
        else:
            raise ValueError(
                f"Unable to parse a version from the input string: {initial}. Is it in the format '(v)x.y.z' (e.g. 'v1.18.2' or '1.18.0')?"
            )

    def check_is_at_least_1_25_0(self, feature: str) -> None:
        if not self >= _ServerVersion(1, 25, 0):
            raise WeaviateUnsupportedFeatureError(feature, str(self), "1.25.0")

    @property
    def supports_tenants_get_grpc(self) -> bool:
        return self >= _ServerVersion(1, 25, 0)


def is_weaviate_too_old(current_version_str: str) -> bool:
    """
    Check if the user should be gently nudged to upgrade their Weaviate server version.

    Parameters
    ----------
    current_version_str : str
        The version of the Weaviate server that the client is connected to. (e.g. "v1.18.2" or "1.18.0")

    Returns
    -------
    bool :
    True if the user should be nudged to upgrade.

    """

    current_version = parse_version_string(current_version_str)
    minimum_version = parse_version_string(MINIMUM_NO_WARNING_VERSION)
    return minimum_version > current_version


def is_weaviate_client_too_old(current_version_str: str, latest_version_str: str) -> bool:
    """
    Check if the user should be gently nudged to upgrade their Weaviate client version.

    Parameters
    ----------
    current_version_str : str
        The version of the Weaviate client that is being used (e.g. "v1.18.2" or "1.18.0")
    latest_version_str : str
        The latest version of the Weaviate client to compare against (e.g. "v1.18.2" or "1.18.0")

    Returns
    -------
    bool :
    True if the user should be nudged to upgrade.
    False if the user is using a valid version or if the version could not be parsed.

    """

    try:
        current_version = parse_version_string(current_version_str)
        latest_major, latest_minor = parse_version_string(latest_version_str)
        minimum_minor = max(latest_minor - MAXIMUM_MINOR_VERSION_DELTA, 0)
        minimum_version = (latest_major, minimum_minor)
        return minimum_version > current_version
    except ValueError:
        return False


def _get_valid_timeout_config(
    timeout_config: Union[Tuple[NUMBER, NUMBER], NUMBER, None]
) -> Tuple[NUMBER, NUMBER]:
    """
    Validate and return TimeOut configuration.

    Parameters
    ----------
    timeout_config : tuple(NUMBERS, NUMBERS) or NUMBERS or None, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            number or, a tuple of two numbers: (connect timeout, read timeout).
            If only one number is passed then both connect and read timeout will be set to
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

    def check_number(num: Union[NUMBER, Tuple[NUMBER, NUMBER], None]) -> bool:
        return isinstance(num, float) or isinstance(num, int)

    if (isinstance(timeout_config, float) or isinstance(timeout_config, int)) and not isinstance(
        timeout_config, bool
    ):
        assert timeout_config is not None
        if timeout_config <= 0.0:
            raise ValueError("'timeout_config' cannot be non-positive number/s!")
        return timeout_config, timeout_config

    if not isinstance(timeout_config, tuple):
        raise TypeError("'timeout_config' should be a (or tuple of) positive number/s!")
    if len(timeout_config) != 2:
        raise ValueError("'timeout_config' must be of length 2!")
    if not (check_number(timeout_config[0]) and check_number(timeout_config[1])) or (
        isinstance(timeout_config[0], bool) and isinstance(timeout_config[1], bool)
    ):
        raise TypeError("'timeout_config' must be tuple of numbers")
    if timeout_config[0] <= 0.0 or timeout_config[1] <= 0.0:
        raise ValueError("'timeout_config' cannot be non-positive number/s!")
    return timeout_config


def _type_request_response(json_response: Any) -> Optional[Dict[str, Any]]:
    if json_response is None:
        return None
    assert isinstance(json_response, dict)
    return json_response


def _to_beacons(uuids: UUIDS, to_class: str = "") -> List[Dict[str, str]]:
    if isinstance(uuids, uuid_lib.UUID) or isinstance(
        uuids, str
    ):  # replace with isinstance(uuids, UUID) in 3.10
        uuids = [uuids]

    if len(to_class) > 0:
        to_class = to_class + "/"

    return [{"beacon": f"weaviate://localhost/{to_class}{uuid_to}"} for uuid_to in uuids]


def _decode_json_response_dict(response: httpx.Response, location: str) -> Optional[Dict[str, Any]]:
    if response is None:
        return None

    if 200 <= response.status_code < 300:
        try:
            json_response = cast(Dict[str, Any], response.json())
            return json_response
        except httpx.DecodingError:
            raise ResponseCannotBeDecodedError(location, response)

    raise UnexpectedStatusCodeError(location, response)


def _decode_json_response_list(
    response: httpx.Response, location: str
) -> Optional[List[Dict[str, Any]]]:
    if response is None:
        return None

    if 200 <= response.status_code < 300:
        try:
            json_response = response.json()
            return cast(list, json_response)
        except httpx.DecodingError:
            raise ResponseCannotBeDecodedError(location, response)
    raise UnexpectedStatusCodeError(location, response)


def _datetime_to_string(value: TIME) -> str:
    if value.tzinfo is None:
        _Warnings.datetime_insertion_with_no_specified_timezone(value)
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.isoformat(sep="T", timespec="microseconds")


def _datetime_from_weaviate_str(string: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(
            "".join(string.rsplit(":", 1) if string[-1] != "Z" else string),
            "%Y-%m-%dT%H:%M:%S.%f%z",
        )
    except ValueError:  # if the string does not have microseconds
        return datetime.datetime.strptime(
            "".join(string.rsplit(":", 1) if string[-1] != "Z" else string),
            "%Y-%m-%dT%H:%M:%S%z",
        )


def __is_list_type(inputs: Any) -> bool:
    try:
        if len(inputs) == 0:
            return False
    except TypeError:
        return False

    return any(
        _is_valid(types, inputs)
        for types in [
            List,
            _ExtraTypes.TF,
            _ExtraTypes.PANDAS,
            _ExtraTypes.NUMPY,
            _ExtraTypes.POLARS,
        ]
    )


def _is_1d_vector(inputs: Any) -> bool:
    try:
        if len(inputs) == 0:
            return False
    except TypeError:
        return False
    if __is_list_type(inputs):
        return not __is_list_type(inputs[0])  # 2D vectors are not 1D vectors
    return False
