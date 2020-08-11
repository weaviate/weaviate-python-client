import validators
import requests
import json
import os
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS


def generate_local_beacon(to_uuid, semantic_type=SEMANTIC_TYPE_THINGS):
    """ Generates a beacon to the given schema class type with the given uuid.

    :param to_uuid:
    :type to_uuid: str
    :param semantic_type: Either things or actions.
                          Defaults to things.
                          Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
    :type semantic_type: str
    :return:
    """
    if not isinstance(to_uuid, str):
        raise TypeError("Expected to_thing_uuid of type str")
    if not validators.uuid(to_uuid):
        raise ValueError("Uuid does not have the propper form")

    return {"beacon": "weaviate://localhost/"+semantic_type+"/"+to_uuid}


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


def is_weaviate_entity_url(input):
    """ Checks if the input follows a normal url like this:
        'weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'

    :param input:
    :type input: str
    :return:
    """
    if not isinstance(input, str):
        return False
    if not input.startswith("weaviate://"):
        return False
    input = input[11:]
    split = input.split("/")
    if len(split) != 3:
        return False
    if split[0] != "localhost":
        if not validators.domain(split[0]):
            return False
    if split[1] != SEMANTIC_TYPE_THINGS and split[1] != SEMANTIC_TYPE_ACTIONS:
        return False
    if not validators.uuid(split[2]):
        return False

    return True


def is_object_url(input):
    """ Validates if an url like http://localhost:8080/v1/things/1c9cd584-88fe-5010-83d0-017cb3fcb446 references a thing.
        it only validates the path not the host or the protocol

    :param input:
    :type input: str
    :return:
    """
    split = input.split("/")
    if len(split) < 3:
        return False
    if not validators.uuid(split[-1]):
        return False
    if not (split[-2] == SEMANTIC_TYPE_ACTIONS or split[-2] == SEMANTIC_TYPE_THINGS):
        return False
    if not split[-3] == "v1":
        return False
    return True


class ParsedUUID:
    def __init__(self, input):
        """ Parses an input string to a ParsedUUID

        :param input:
        :type input: str
        :return:
            TypeError: If parameter has the wrong type.
        """
        if not isinstance(input, str):
            raise TypeError("uuid must be of type str but was: " + str(type(input)))

        self.is_weaviate_url = is_weaviate_entity_url(input)
        self.is_object_url = is_object_url(input)

        self.uuid = input
        self.semantic_type = None
        if self.is_weaviate_url or self.is_object_url:
            split = input.split("/")
            self.uuid = split[-1]
            self.semantic_type = split[-2]

        self.is_valid = validators.uuid(self.uuid)


def is_semantic_type(semantic_type):
    """

    :param semantic_type:
    :type semantic_type: str
    :return:
    :rtype: bool
    :raises:
        TypeError
    """
    if not isinstance(semantic_type, str):
        raise TypeError("Semantic type must be str but is "+str(type(semantic_type)))
    if semantic_type == SEMANTIC_TYPE_THINGS or semantic_type == SEMANTIC_TYPE_ACTIONS:
        return True
    return False


def get_uuid_from_weaviate_url(url):
    """

    :param url: Along this form: 'weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'
    :type url: str
    :return:
    """
    return url.split("/")[-1]


def get_domain_from_weaviate_url(url):
    """

    :param url: Along this form: 'weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'
    :type url: str
    :return:
    """
    return url[11:].split("/")[0]


def _is_sub_schema(sub_schema, schema):
    """

    :param sub_schema: the smaller schema that should be contained in the other schema
    :param schema: the
    :return:
    """
    is_sub_set_actions = _is_sub_schema_schema_class(sub_schema, schema, "actions")
    is_sub_set_things = _is_sub_schema_schema_class(sub_schema, schema, "things")
    return is_sub_set_actions and is_sub_set_things


def _is_sub_schema_schema_class(sub_schema, schema, schema_class):
    if schema_class in sub_schema:
        if schema_class in schema:
            schema_classes = schema[schema_class].get("classes", [])
        else:
            # Even if schema_class is not present it might be as a empty node
            # only the classes itself should be important for the schema comparison
            schema_classes = []

        sub_schema_classes = sub_schema[schema_class].get("classes", [])

        return _compare_class_sets(sub_schema_classes, schema_classes)

    return True


def _compare_class_sets(sub_set, set):
    """

    :param sub_set:
    :type sub_set: list
    :param set:
    :type set: list
    :return: True if subset in set
    """
    for sub_set_class in sub_set:
        found = False
        for set_class in set:
            if sub_set_class["class"] == set_class["class"]:
                if _compare_properties(sub_set_class["properties"], set_class["properties"]):
                    found = True
                    break
        if not found:
            return False
    return True


def _compare_properties(sub_set, set):
    """

    :param sub_set:
    :param set:
    :return: True if subset in set
    """
    for sub_set_property in sub_set:
        found = False
        for set_property in set:
            if sub_set_property["name"] == set_property["name"]:
                found = True
                break
        if not found:
            return False
    return True