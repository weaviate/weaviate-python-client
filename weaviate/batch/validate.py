import dateutil.parser

TYPE_MAPPINGS = {
    "string": str,
    "int": int,
    "boolean": bool,
    "number": float,
    "date": str,
    "geoCoordinates": dict,
    "phoneNumber": dict,
    "blob": str,
}


def validate_data_object(data_object: dict, properties: list):
    """
    Takes in a properties list and produces a validation schema from it.
    For each item in the data_object this validates whether the types match those specified in the schema
    """
    schema = _create_schema_from_properties(properties)
    for key, value in data_object.items():
        if key not in schema:
            raise ValueError("Invalid key: `{}`".format(key))
        if schema[key]["type"] not in TYPE_MAPPINGS:
            raise ValueError("Unsupported type `{}`".format(schema[key]["type"]))
        if schema[key]["type"] == "date":
            if not _validate_date(value):
                raise ValueError("Invalid date: `{}`".format(value))
        elif schema[key]["type"] == "geoCoordinates":
            if not _validate_geo(value):
                raise ValueError("Invalid geoCoordinates: `{}`".format(value))
        elif schema[key]["type"] == "phoneNumber":
            if not _validate_phonenumber(value):
                raise ValueError("Invalid phoneNumber: `{}`".format(value))
        else:
            if not isinstance(value, TYPE_MAPPINGS[schema[key]["type"]]):
                raise ValueError(
                    "Invalid value: `{}` expected type `{}` but got type `{}`".format(
                        value, TYPE_MAPPINGS[schema[key]["type"]], type(value)
                    )
                )
    return True


def _validate_date(datestring: str) -> bool:
    "Validates whether a string is a correctly formatted datetime in the RFC 3339 format"
    try:
        # This is a pretty fuzzy and loose check but does conform to the RFC 3339 format
        dateutil.parser.isoparse(datestring)
        return True
    except ValueError:
        return False


def _validate_geo(geo: dict) -> bool:
    """
    Validates a that a geo dict contains the keys latitude and longitude
    """
    if "latitude" not in geo or "longitude" not in geo:
        return False
    return True


def _validate_phonenumber(phonenumber: dict) -> bool:
    """
    Validates a phone dict object. If the number `input` is not in international format
    then there must be a key for `defaultCountry` in the dict.
    """
    if not _check_phonenumber_is_international_fmt(phonenumber["input"]):
        if "defaultCountry" not in phonenumber:
            return False
    return True


def _check_phonenumber_is_international_fmt(phonenumber: str):
    """
    Checks whether a provided `phonenumber` is in a international phone number format.
    """
    if phonenumber[0] == "+":
        return True
    return False


def _create_schema_from_properties(properties: list):
    """
    Iterates through each dict element in properties, if the dict contains
    a key named "dataType" then it is added to the schema.
    """
    schema = {}
    for prop in properties:
        if "dataType" in prop:
            schema[prop["name"]] = {"type": prop["dataType"][0]}
    return schema
