from .exceptions import SchemaValidationException


def validate_schema(schema):
    """

    :param schema:
    :type schema: dict
    :return: None if parsing was successful
    :raises SchemaValidationException: if the schema could not be validated against the standard format.
    """
    _check_schema_class_type_definitions(schema.keys())

    for class_type in schema:
        _check_schema_class_types(class_type, schema[class_type])

        for weaviate_class in schema[class_type]["classes"]:
            _check_class(weaviate_class)


def _check_class(class_definition):
    """

    :param class_definition:
    :type class_definition: dict
    :return:
    """
    # check mandatory keys
    if "class" not in class_definition:
        raise SchemaValidationException(f"\"class\" key is missing in class definition.")

    # check optional keys
    for key in class_definition.keys():
        # Check if key is known
        if key not in ["class", "description", "vectorizeClassName", "keywords", "properties"]:
            raise SchemaValidationException(f"{key} is not a known class definition key.")
        # check if key is right type
        if key == "vectorizeClassName":
            _check_key_type(key, class_definition[key], bool)
        if key in ["description", "class"]:
            _check_key_type(key, class_definition[key], str)
        if key in ["keywords", "properties"]:
            _check_key_type(key, class_definition[key], list)

    if "keywords" in class_definition:
        _check_keywords(class_definition["keywords"])

    if "properties" in class_definition:
        for class_property in class_definition["properties"]:
            _check_property(class_property)


def _check_key_type(key, value, expected_type):
    type_of_value = type(value)
    if type(value) != expected_type:
        raise SchemaValidationException(f"{key} is type {type_of_value} but should be {expected_type}.")


def _check_keywords(keywords):
    """

    :param keywords: the keywords list of a class or property
    :type keywords: list
    :return:
    """
    for word_item in keywords:
        if "keyword" not in word_item:
            raise SchemaValidationException("\"keywords\" item does not contain \"keyword\" key.")
        _check_key_type("keyword", word_item["keyword"], str)
        if "weight" in word_item:
            _check_key_type("weight", word_item["weight"], float)
        for word_key in word_item:
            if word_key not in ["keyword", "weight"]:
                raise SchemaValidationException(f"Unknown key in \"keywords\" item: {word_key}")


def _check_property(class_property):
    """

    :param class_property:
    :type class_property: dict
    :return:
    """
    if "dataType" not in class_property:
        raise SchemaValidationException("Property does not contain \"dataType\"")
    if "name" not in class_property:
        raise SchemaValidationException("Property does not contain \"name\"")

    for key in class_property:
        if key not in ["dataType", "name", "vectorizePropertyName", "keywords", "cardinality", "description", "index"]:
            raise SchemaValidationException(f"Property key {key} is not known.")

        # Test types
        if key in ["dataType", "keywords"]:
            _check_key_type(key, class_property[key], list)
        if key in ["name", "cardinality", "description"]:
            _check_key_type(key, class_property[key], str)
        if key in ["vectorizePropertyName", "index"]:
            _check_key_type(key, class_property[key], bool)

    # Test cardinality
    if "cardinality" in class_property:
        cardinality = class_property["cardinality"]
        if cardinality != "many" and cardinality != "atMostOne":
            raise SchemaValidationException(
                f"Property cardinality must either be \"many\" or \"atMostOne\" but was {cardinality}")

    # Test keywords
    if "keywords" in class_property:
        _check_keywords(class_property["keywords"])

    # Test dataType types
    for data_type in class_property["dataType"]:
        _check_key_type("dataType", data_type, str)


def _check_schema_class_types(class_type, content):
    """ Only classes is mandatory in the class type

    :param class_type: things or actions
    :param content:
    :return:
    """
    if not ("classes" in content):
        raise SchemaValidationException(f"{class_type} does not contain mandatory key \"classes\".")
    if type(content["classes"]) != list:
        raise SchemaValidationException(f"\"classes\" in {class_type} must be of type list.")


def _check_schema_class_type_definitions(keys):
    """ Checks if the keys that define the schema class types are valid.
    :param keys:
    :type keys: dict_keys
    :return:
    """
    if len(keys) == 0:
        # at least one type must be defined
        raise SchemaValidationException("No schema class types are defined in the schema. "
                                        "Please specify \"actions\" and/or \"things\".")
    for key in keys:
        if key not in ["things", "actions"]:
            raise SchemaValidationException(f"{key} is not a valid schema class type.")
