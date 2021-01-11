"""
Schema validation module.
"""
from typing import Any
from weaviate.exceptions import SchemaValidationException


def validate_schema(schema: dict) -> None:
    """
    Validate schema.

    Parameters
    ----------
    schema : dict
        Schema to be validated.

    Raises
    ------
    SchemaValidationException
        If the schema could not be validated against the standard format.
    """

    # check if schema has only "classes" as keys
    if len(schema) != 1 or "classes" not in schema:
        raise SchemaValidationException('each schema has to have only "classes" \
                    in the first level of the JSON format file/parameter/object')
    # check if "classes" is of type list
    _check_key_type("classes", schema["classes"], list)
    # check if each class in the "classes" is a valid class
    for weaviate_class in schema["classes"]:
        check_class(weaviate_class)


def check_class(class_definition: dict) -> None:
    """
    Validate a class against the standard class format.

    Parameters
    ----------
    class_definition : dict
        The definition of the class to be validated.

    Raises
    ------
    SchemaValidationException
        If the class could not be validated against the standard class format.
    """

    # check mandatory keys
    if "class" not in class_definition:
        raise SchemaValidationException('"class" key is missing in class definition.')

    # check optional keys
    for key in class_definition.keys():
        # Check if key is known
        if key not in ["class", "vectorIndexType", "vectorIndexConfig", "moduleConfig",\
            "description", "vectorizer", "properties"]:
            raise SchemaValidationException(f'"{key}" is not a known class definition key.')
        # check if key is right type
        if key in ["class", "vectorIndexType", "description", "vectorizer"]:
            _check_key_type(key, class_definition[key], str)
        if key in ["vectorIndexConfig", "moduleConfig"]:
            _check_key_type(key, class_definition[key], dict)
        if key in ["properties"]:
            _check_key_type(key, class_definition[key], list)
        # TODO check in depth dicts

    if "properties" in class_definition:
        for class_property in class_definition["properties"]:
            check_property(class_property)


def check_property(class_property: dict) -> None:
    """
    Validate a class property against the standard class property.

    Parameters
    ----------
    class_property : dict
        The class property to be validated.

    Raises
    ------
    SchemaValidationException
        If the class property could not be validated against\
        the standard class property format.
    """

    # mandatory fields
    if "dataType" not in class_property:
        raise SchemaValidationException('Property does not contain "dataType"')
    if "name" not in class_property:
        raise SchemaValidationException('Property does not contain "name"')

    for key in class_property:
        # check for misspelled and/or non-existent properties
        if key not in ["dataType", "name", "moduleConfig", "description", "indexInverted"]:
            raise SchemaValidationException(f'Property "{key}" is not known.')

        # Test types
        if key in ["dataType"]:
            _check_key_type(key, class_property[key], list)
        if key in ["name", "description"]:
            _check_key_type(key, class_property[key], str)
        if key in ["indexInverted"]:
            _check_key_type(key, class_property[key], bool)
        if key in ["moduleConfig"]:
            _check_key_type(key, class_property[key], dict)
            # TODO check "moduleConfig" hierarch types and keys

    # Test dataType types
    for data_type in class_property["dataType"]:
        _check_key_type("dataType", data_type, str)


def _check_key_type(key: str, value: Any, expected_type: Any) -> None:
    """
    Check if value is of an expected type.

    Parameters
    ----------
    key : str
        The key for which to check data type.
    value : Any
        The value of the 'key' for which to check data type.
    expected_type : Any
        The expected data type of the 'value'.

    Raises
    ------
    SchemaValidationException
        If the 'value' is of wrong data type.
    """

    if not isinstance(value, expected_type):
        raise SchemaValidationException(f'"{key}" is type {type(value)} \
                                        but should be {expected_type}.')
