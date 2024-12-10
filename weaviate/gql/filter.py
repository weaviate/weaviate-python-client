"""
GraphQL filters for `Get` and `Aggregate` commands.
GraphQL abstract class for GraphQL commands to inherit from.
"""

import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from enum import Enum
from json import dumps
from typing import Any, Tuple, Union

from weaviate.error_msgs import FILTER_BEACON_V14_CLS_NS_W
from weaviate.util import get_vector, _sanitize_str

VALUE_LIST_TYPES = {
    "valueStringList",
    "valueTextList",
    "valueIntList",
    "valueNumberList",
    "valueBooleanList",
    "valueDateList",
}

VALUE_ARRAY_TYPES = {
    "valueStringArray",
    "valueTextArray",
    "valueIntArray",
    "valueNumberArray",
    "valueBooleanArray",
    "valueDateArray",
}

VALUE_PRIMITIVE_TYPES = {
    "valueString",
    "valueText",
    "valueInt",
    "valueNumber",
    "valueDate",
    "valueBoolean",
    "valueGeoRange",
}

ALL_VALUE_TYPES = VALUE_LIST_TYPES.union(VALUE_ARRAY_TYPES).union(VALUE_PRIMITIVE_TYPES)
VALUE_TYPES = VALUE_ARRAY_TYPES.union(VALUE_PRIMITIVE_TYPES)

WHERE_OPERATORS = [
    "And",
    "ContainsAll",
    "ContainsAny",
    "Equal",
    "GreaterThan",
    "GreaterThanEqual",
    "IsNull",
    "LessThan",
    "LessThanEqual",
    "Like",
    "NotEqual",
    "Or",
    "WithinGeoRange",
]


class MediaType(Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    THERMAL = "thermal"
    DEPTH = "depth"
    IMU = "imu"


class GraphQL(ABC):
    """
    A base abstract class for GraphQL commands, such as Get, Aggregate.
    """

    @abstractmethod
    def build(self) -> str:
        """
        Build method to be overloaded by the child classes. It should return the
        GraphQL query as a str.

        Returns
        -------
        str
            The query.
        """


class Filter(ABC):
    """
    A base abstract class for all filters.
    """

    def __init__(self, content: dict):
        """
        Initialize a Filter class instance.

        Parameters
        ----------
        content : dict
            The content of the `Filter` clause.
        """

        if not isinstance(content, dict):
            raise TypeError(
                f"{self.__class__.__name__} filter is expected to "
                f"be type dict but is {type(content)}"
            )
        self._content = deepcopy(content)

    @abstractmethod
    def __str__(self) -> str:
        """
        Should be implemented in each inheriting class.
        """

    @property
    def content(self) -> dict:
        return self._content


class NearText(Filter):
    """
    NearText class used to filter weaviate objects. Can be used with text models only (text2vec).
    E.g.: text2vec-contextionary, text2vec-transformers.
    """

    def __init__(self, content: dict):
        """
        Initialize a NearText class instance.

        Parameters
        ----------
        content : dict
            The content of the `nearText` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """

        super().__init__(content)

        _check_concept(self._content)

        if "certainty" in self._content:
            if "distance" in self._content:
                raise ValueError(
                    "Cannot have both 'certainty' and 'distance' at the same time. "
                    "Only one is accepted."
                )
            _check_type(var_name="certainty", value=self._content["certainty"], dtype=float)
        if "distance" in self._content:
            _check_type(var_name="distance", value=self._content["distance"], dtype=float)

        if "moveTo" in self._content:
            _check_direction_clause(self._content["moveTo"])

        if "moveAwayFrom" in self._content:
            _check_direction_clause(self._content["moveAwayFrom"])

        if "autocorrect" in self._content:
            _check_type(var_name="autocorrect", value=self._content["autocorrect"], dtype=bool)

    def __str__(self) -> str:
        near_text = f'nearText: {{concepts: {dumps(self._content["concepts"])}'
        if "certainty" in self._content:
            near_text += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            near_text += f' distance: {self._content["distance"]}'
        if "moveTo" in self._content:
            move_to = self._content["moveTo"]
            near_text += f' moveTo: {{force: {move_to["force"]}'
            if "concepts" in move_to:
                near_text += f' concepts: {dumps(move_to["concepts"])}'
            if "objects" in move_to:
                near_text += _move_clause_objects_to_str(move_to["objects"])
            near_text += "}"
        if "moveAwayFrom" in self._content:
            move_away_from = self._content["moveAwayFrom"]
            near_text += f' moveAwayFrom: {{force: {move_away_from["force"]}'
            if "concepts" in move_away_from:
                near_text += f' concepts: {dumps(move_away_from["concepts"])}'
            if "objects" in move_away_from:
                near_text += _move_clause_objects_to_str(move_away_from["objects"])
            near_text += "}"
        if "autocorrect" in self._content:
            near_text += f' autocorrect: {_bool_to_str(self._content["autocorrect"])}'
        if "targetVector" in self._content:
            near_text += f' targetVectors: "{self._content["targetVector"]}"'
        return near_text + "} "


class NearVector(Filter):
    """
    NearVector class used to filter weaviate objects.
    """

    def __init__(self, content: dict):
        """
        Initialize a NearVector class instance.

        Parameters
        ----------
        content : list
            The content of the `nearVector` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        KeyError
            If 'content' does not contain "vector".
        TypeError
            If 'content["vector"]' is not of type list.
        AttributeError
            If invalid 'content' keys are provided.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """

        super().__init__(content)

        if "vector" not in self._content:
            raise KeyError("No 'vector' key in `content` argument.")

        # Check optional fields
        if "certainty" in self._content:
            if "distance" in self._content:
                raise ValueError(
                    "Cannot have both 'certainty' and 'distance' at the same time. "
                    "Only one is accepted."
                )
            _check_type(var_name="certainty", value=self._content["certainty"], dtype=float)
        if "distance" in self._content:
            _check_type(var_name="distance", value=self._content["distance"], dtype=float)

        self._content["vector"] = get_vector(self._content["vector"])

    def __str__(self) -> str:
        near_vector = f'nearVector: {{vector: {dumps(self._content["vector"])}'
        if "certainty" in self._content:
            near_vector += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            near_vector += f' distance: {self._content["distance"]}'
        if "targetVector" in self._content:
            near_vector += f' targetVectors: "{self._content["targetVector"]}"'
        return near_vector + "} "


class NearObject(Filter):
    """
    NearObject class used to filter weaviate objects.
    """

    def __init__(self, content: dict, is_server_version_14: bool):
        """
        Initialize a NearVector class instance.

        Parameters
        ----------
        content : list
            The content of the `nearVector` clause.
        is_server_version_14 : bool
            Whether the Server version is >= 1.14.0.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If 'content' has key "certainty"/"distance" but the value is not float.
        TypeError
            If 'id'/'beacon' key does not have a value of type str!
        """

        super().__init__(content)

        if ("id" in self._content) and ("beacon" in self._content):
            raise ValueError("The 'content' argument should contain EITHER `id` OR `beacon`!")

        if "id" in self._content:
            self.obj_id = "id"
        else:
            self.obj_id = "beacon"
            if is_server_version_14 and len(self._content["beacon"].strip("/").split("/")) == 4:
                warnings.warn(
                    message=FILTER_BEACON_V14_CLS_NS_W,
                    category=DeprecationWarning,
                    stacklevel=1,
                )

        _check_type(var_name=self.obj_id, value=self._content[self.obj_id], dtype=str)

        if "certainty" in self._content:
            if "distance" in self._content:
                raise ValueError(
                    "Cannot have both 'certainty' and 'distance' at the same time. "
                    "Only one is accepted."
                )
            _check_type(var_name="certainty", value=self._content["certainty"], dtype=float)
        if "distance" in self._content:
            _check_type(var_name="distance", value=self._content["distance"], dtype=float)

    def __str__(self) -> str:
        near_object = f'nearObject: {{{self.obj_id}: "{self._content[self.obj_id]}"'
        if "certainty" in self._content:
            near_object += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            near_object += f' distance: {self._content["distance"]}'
        if "targetVector" in self._content:
            near_object += f' targetVectors: "{self._content["targetVector"]}"'
        return near_object + "} "


class Ask(Filter):
    """
    Ask class used to filter weaviate objects by asking a question.
    """

    def __init__(self, content: dict):
        """
        Initialize a Ask class instance.

        Parameters
        ----------
        content : list
            The content of the `ask` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        TypeError
            If 'content'  has key "properties" but the type is not list or str.
        """

        super().__init__(content)

        if "question" not in self._content:
            raise ValueError('Mandatory "question" key not present in the "content"!')

        _check_type(var_name="question", value=self._content["question"], dtype=str)
        if "certainty" in self._content:
            if "distance" in self._content:
                raise ValueError(
                    "Cannot have both 'certainty' and 'distance' at the same time. "
                    "Only one is accepted."
                )
            _check_type(var_name="certainty", value=self._content["certainty"], dtype=float)
        if "distance" in self._content:
            _check_type(var_name="distance", value=self._content["distance"], dtype=float)

        if "autocorrect" in self._content:
            _check_type(var_name="autocorrect", value=self._content["autocorrect"], dtype=bool)

        if "rerank" in self._content:
            _check_type(var_name="rerank", value=self._content["rerank"], dtype=bool)

        if "properties" in self._content:
            _check_type(var_name="properties", value=self._content["properties"], dtype=(list, str))
            if isinstance(self._content["properties"], str):
                self._content["properties"] = [self._content["properties"]]

    def __str__(self) -> str:
        ask = f'ask: {{question: {dumps(self._content["question"])}'
        if "certainty" in self._content:
            ask += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            ask += f' distance: {self._content["distance"]}'
        if "properties" in self._content:
            ask += f' properties: {dumps(self._content["properties"])}'
        if "autocorrect" in self._content:
            ask += f' autocorrect: {_bool_to_str(self._content["autocorrect"])}'
        if "rerank" in self._content:
            ask += f' rerank: {_bool_to_str(self._content["rerank"])}'
        return ask + "} "


class NearMedia(Filter):
    def __init__(
        self,
        content: dict,
        media_type: MediaType,
    ):
        """
        Initialize a NearMedia class instance.

        Parameters
        ----------
        content : list
            The content of the `near<Media>` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content["<media>"]' is not of type str.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """

        super().__init__(content)

        self._media_type = media_type

        if self._media_type.value not in self._content:
            raise ValueError(f'"content" is missing the mandatory key "{self._media_type.value}"!')

        _check_type(
            var_name=self._media_type.value, value=self._content[self._media_type.value], dtype=str
        )
        if "certainty" in self._content:
            if "distance" in self._content:
                raise ValueError(
                    "Cannot have both 'certainty' and 'distance' at the same time. "
                    "Only one is accepted."
                )
            _check_type(var_name="certainty", value=self._content["certainty"], dtype=float)
        if "distance" in self._content:
            _check_type(var_name="distance", value=self._content["distance"], dtype=float)

    def __str__(self) -> str:
        media = self._media_type.value.capitalize()
        if self._media_type == MediaType.IMU:
            media = self._media_type.value.upper()
        near_media = (
            f'near{media}: {{{self._media_type.value}: "{self._content[self._media_type.value]}"'
        )
        if "certainty" in self._content:
            near_media += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            near_media += f' distance: {self._content["distance"]}'
        if "targetVector" in self._content:
            near_media += f' targetVectors: "{self._content["targetVector"]}"'
        return near_media + "} "


class NearImage(NearMedia):
    """
    NearImage class used to filter weaviate objects.
    """

    def __init__(
        self,
        content: dict,
    ):
        """
        Initialize a NearImage class instance.

        Parameters
        ----------
        content : list
            The content of the `nearImage` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content["image"]' is not of type str.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """
        super().__init__(content, MediaType.IMAGE)


class NearVideo(NearMedia):
    """
    NearVideo class used to filter weaviate objects.
    """

    def __init__(
        self,
        content: dict,
    ):
        """
        Initialize a NearVideo class instance.

        Parameters
        ----------
        content : list
            The content of the `nearVideo` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content["video"]' is not of type str.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """
        super().__init__(content, MediaType.VIDEO)


class NearAudio(NearMedia):
    """
    NearAudio class used to filter weaviate objects.
    """

    def __init__(
        self,
        content: dict,
    ):
        """
        Initialize a NearAudio class instance.

        Parameters
        ----------
        content : list
            The content of the `nearAudio` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content["audio"]' is not of type str.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """
        super().__init__(content, MediaType.AUDIO)


class NearDepth(NearMedia):
    """
    NearDepth class used to filter weaviate objects.
    """

    def __init__(
        self,
        content: dict,
    ):
        """
        Initialize a NearDepth class instance.

        Parameters
        ----------
        content : list
            The content of the `nearDepth` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content["depth"]' is not of type str.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """
        super().__init__(content, MediaType.DEPTH)


class NearThermal(NearMedia):
    """
    NearThermal class used to filter weaviate objects.
    """

    def __init__(
        self,
        content: dict,
    ):
        """
        Initialize a NearThermal class instance.

        Parameters
        ----------
        content : list
            The content of the `nearThermal` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content["thermal"]' is not of type str.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """
        super().__init__(content, MediaType.THERMAL)


class NearIMU(NearMedia):
    """
    NearIMU class used to filter weaviate objects.
    """

    def __init__(
        self,
        content: dict,
    ):
        """
        Initialize a NearIMU class instance.

        Parameters
        ----------
        content : list
            The content of the `nearIMU` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content["imu"]' is not of type str.
        ValueError
            If 'content'  has key "certainty"/"distance" but the value is not float.
        """
        super().__init__(content, MediaType.IMU)


class Sort(Filter):
    """
    Sort filter class used to sort weaviate objects.
    """

    def __init__(self, content: Union[dict, list]):
        """
        Initialize a Where filter class instance.

        Parameters
        ----------
        content : list or dict
            The content of the `sort` filter clause or a single clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If a mandatory key is missing in the filter content.
        """

        # content is a empty list because it is going to the the list with sort clauses.

        super().__init__(content={"sort": []})

        self.add(content=content)

    def add(self, content: Union[dict, list]) -> None:
        """
        Add more sort clauses to the already existing sort clauses.

        Parameters
        ----------
        content : list or dict
            The content of the `sort` filter clause or a single clause to be added to the already
            existing ones.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If a mandatory key is missing in the filter content.
        """

        if isinstance(content, dict):
            content = [content]

        if not isinstance(content, list):
            raise TypeError(f"'content' must be of type dict or list. Given type: {type(content)}.")

        if len(content) == 0:
            raise ValueError("'content' cannot be an empty list.")

        for clause in content:
            if "path" not in clause or "order" not in clause:
                raise ValueError(
                    "One of the sort clause is missing required fields: 'path' and/or 'order'."
                )

            _check_type(
                var_name="path",
                value=clause["path"],
                dtype=list,
            )
            _check_type(
                var_name="order",
                value=clause["order"],
                dtype=str,
            )

            self._content["sort"].append(
                {
                    "path": clause["path"],
                    "order": clause["order"],
                }
            )

    def __str__(self) -> str:
        sort = "sort: ["
        for clause in self._content["sort"]:
            sort += f"{{ path: {dumps(clause['path'])} order: {clause['order']} }} "

        sort += "]"
        return sort


class Where(Filter):
    """
    Where filter class used to filter weaviate objects.
    """

    def __init__(self, content: dict):
        """
        Initialize a Where filter class instance.

        Parameters
        ----------
        content : dict
            The content of the `where` filter clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If a mandatory key is missing in the filter content.
        """

        super().__init__(content)

        if "path" in self._content:
            self.is_filter = True
            self._parse_filter(self._content)
        elif "operands" in self._content:
            self.is_filter = False
            self._parse_operator(self._content)
        else:
            raise ValueError(
                "Filter is missing required fields `path` or `operands`." f" Given: {self._content}"
            )

    def _parse_filter(self, content: dict) -> None:
        """
        Set filter fields for the Where filter.

        Parameters
        ----------
        content : dict
            The content of the `where` filter clause.

        Raises
        ------
        ValueError
            If 'content' is missing required fields.
        """

        if "operator" not in content:
            raise ValueError("Filter is missing required field `operator`. " f"Given: {content}")
        if content["operator"] not in WHERE_OPERATORS:
            raise ValueError(
                f"Operator {content['operator']} is not allowed. "
                f"Allowed operators are: {', '.join(WHERE_OPERATORS)}"
            )
        self.path = dumps(content["path"])
        self.operator = content["operator"]
        self.value_type = _find_value_type(content)
        self.value = content[self.value_type]

        if self.operator == "WithinGeoRange" and self.value_type != "valueGeoRange":
            raise ValueError(
                f"Operator {self.operator} requires a value of type valueGeoRange. "
                f"Given value type: {self.value_type}"
            )

    def _parse_operator(self, content: dict) -> None:
        """
        Set operator fields for the Where filter.

        Parameters
        ----------
        content : dict
            The content of the `where` filter clause.

        Raises
        ------
        ValueError
            If 'content' is missing required fields.
        """

        if "operator" not in content:
            raise ValueError("Filter is missing required field `operator`." f" Given: {content}")
        if content["operator"] not in WHERE_OPERATORS:
            raise ValueError(
                f"Operator {content['operator']} is not allowed. "
                f"Allowed operators are: {WHERE_OPERATORS}"
            )
        _content = deepcopy(content)
        self.operator = _content["operator"]
        self.operands = []
        for operand in _content["operands"]:
            self.operands.append(Where(operand))

    def __str__(self) -> str:
        if self.is_filter:
            gql = f"where: {{path: {self.path} operator: {self.operator} {_convert_value_type(self.value_type)}: "
            if self.value_type in [
                "valueInt",
                "valueNumber",
                "valueIntArray",
                "valueNumberArray",
                "valueIntList",
                "valueNumberList",
            ]:
                if self.value_type in [
                    "valueIntList",
                    "valueNumberList",
                    "valueIntList",
                    "valueNumberList",
                ]:
                    _check_is_list(self.value, self.value_type)
                gql += f"{self.value}}}"
            elif self.value_type in [
                "valueText",
                "valueString",
                "valueTextList",
                "valueStringList",
                "valueTextArray",
                "valueStringArray",
            ]:
                if self.value_type in [
                    "valueTextList",
                    "valueStringList",
                    "valueTextArray",
                    "valueStringArray",
                ]:
                    _check_is_list(self.value, self.value_type)
                if isinstance(self.value, list):
                    val = [_sanitize_str(v) for v in self.value]
                    gql += f"{_render_list(val)}}}"
                else:
                    gql += f"{_sanitize_str(self.value)}}}"
            elif self.value_type in ["valueBoolean", "valueBooleanArray", "valueBooleanList"]:
                if self.value_type in ["valueBooleanArray", "valueBooleanList"]:
                    _check_is_list(self.value, self.value_type)
                if isinstance(self.value, list):
                    gql += f"{_render_list(self.value)}}}"
                else:
                    gql += f"{_bool_to_str(self.value)}}}"
            elif self.value_type in ["valueDateArray", "valueDateList"]:
                _check_is_list(self.value, self.value_type)
                gql += f"{_render_list_date(self.value)}}}"
            elif self.value_type == "valueGeoRange":
                _check_is_not_list(self.value, self.value_type)
                gql += f"{_geo_range_to_str(self.value)}}}"
            else:
                gql += f'"{self.value}"}}'
            return gql + " "

        operands_str = []
        for operand in self.operands:
            # remove the `where: ` from the operands and the last space
            operands_str.append(str(operand)[7:-1])
        operands = ", ".join(operands_str)
        return f"where: {{operator: {self.operator} operands: [{operands}]}} "


def _convert_value_type(_type: str) -> str:
    """Convert the value type to match `json` formatting required by the Weaviate-defined
    GraphQL endpoints. NOTE: This is crucially different to the Batch REST endpoints wherein
    the where filter is also used.

    Parameters
    ----------
    _type : str
        The Python-defined type to be converted.

    Returns
    -------
    str
        The string interpretation of the type in Weaviate-defined `json` format.
    """
    if _type == "valueTextArray" or _type == "valueTextList":
        return "valueText"
    elif _type == "valueStringArray" or _type == "valueStringList":
        return "valueString"
    elif _type == "valueIntArray" or _type == "valueIntList":
        return "valueInt"
    elif _type == "valueNumberArray" or _type == "valueNumberList":
        return "valueNumber"
    elif _type == "valueBooleanArray" or _type == "valueBooleanList":
        return "valueBoolean"
    elif _type == "valueDateArray" or _type == "valueDateList":
        return "valueDate"
    else:
        return _type


def _render_list(input_list: list) -> str:
    """Convert a list of values to string (lowercased) to match `json` formatting.

    Parameters
    ----------
    input_list : list
        The value to be converted

    Returns
    -------
    str
        The string interpretation of the value in `json` format.
    """
    str_list = ",".join(str(item) for item in input_list)
    return f"[{str_list}]"


def _render_list_date(input_list: list) -> str:
    str_list = ",".join('"' + str(item) + '"' for item in input_list)
    return f"[{str_list}]"


def _check_is_list(value: Any, _type: str) -> None:
    """Checks whether the provided value is a list to match the given `value_type`.

    Parameters
    ----------
    value : list
        The value to be checked.
    _type : str
        The type to be checked against.

    Raises
    ------
    TypeError
        If the value is not a list.
    """
    if not isinstance(value, list):
        raise TypeError(
            f"Must provide a list when constructing where filter for {_type} with {value}"
        )


def _check_is_not_list(value: Any, _type: str) -> None:
    """Checks whether the provided value is a list to match the given `value_type`.

    Parameters
    ----------
    value : list
        The value to be checked.
    _type : str
        The type to be checked against.

    Raises
    ------
    TypeError
        If the value is a list.
    """
    if isinstance(value, list):
        raise TypeError(
            f"Cannot provide a list when constructing where filter for {_type} with {value}"
        )


def _geo_range_to_str(value: dict) -> str:
    """
    Convert the valueGeoRange object to match `json` formatting.

    Parameters
    ----------
    value : dict
        The value to be converted.

    Returns
    -------
    str
        The string interpretation of the value in `json` format.
    """
    latitude = value["geoCoordinates"]["latitude"]
    longitude = value["geoCoordinates"]["longitude"]
    distance = value["distance"]["max"]
    return f"{{ geoCoordinates: {{ latitude: {latitude} longitude: {longitude} }} distance: {{ max: {distance} }}}}"


def _bool_to_str(value: bool) -> str:
    """
    Convert a bool value to string (lowercased) to match `json` formatting.

    Parameters
    ----------
    value : bool
        The value to be converted

    Returns
    -------
    str
        The string interpretation of the value in `json` format.
    """

    if value is True:
        return "true"
    return "false"


def _check_direction_clause(direction: dict) -> None:
    """
    Validate the direction sub clause.

    Parameters
    ----------
    direction : dict
        A sub clause of the Explore filter.

    Raises
    ------
    TypeError
        If 'direction' is not a dict.
    TypeError
        If the value of the "force" key is not float.
    ValueError
        If no "force" key in the 'direction'.
    """

    _check_type(var_name="moveXXX", value=direction, dtype=dict)

    if ("concepts" not in direction) and ("objects" not in direction):
        raise ValueError("The 'move' clause should contain `concepts` OR/AND `objects`!")

    if "concepts" in direction:
        _check_concept(direction)
    if "objects" in direction:
        _check_objects(direction)
    if "force" not in direction:
        raise ValueError("'move' clause needs to state a 'force'")
    _check_type(var_name="force", value=direction["force"], dtype=float)


def _check_concept(content: dict) -> None:
    """
    Validate the concept sub clause.

    Parameters
    ----------
    content : dict
        An Explore (sub) clause to check for 'concepts'.

    Raises
    ------
    ValueError
        If no "concepts" key in the 'content' dict.
    TypeError
        If the value of the  "concepts" is of wrong type.
    """

    if "concepts" not in content:
        raise ValueError("No concepts in content")

    _check_type(
        var_name="concepts",
        value=content["concepts"],
        dtype=(list, str),
    )
    if isinstance(content["concepts"], str):
        content["concepts"] = [content["concepts"]]


def _check_objects(content: dict) -> None:
    """
    Validate the `objects` sub clause of the `move` clause.

    Parameters
    ----------
    content : dict
        An Explore (sub) clause to check for 'objects'.

    Raises
    ------
    ValueError
        If no "concepts" key in the 'content' dict.
    TypeError
        If the value of the  "concepts" is of wrong type.
    """

    _check_type(var_name="objects", value=content["objects"], dtype=(list, dict))
    if isinstance(content["objects"], dict):
        content["objects"] = [content["objects"]]

    if len(content["objects"]) == 0:
        raise ValueError("'moveXXX' clause specifies 'objects' but no value provided.")

    for obj in content["objects"]:
        if len(obj) != 1 or ("id" not in obj and "beacon" not in obj):
            raise ValueError(
                "Each object from the `move` clause should have ONLY `id` OR " "`beacon`!"
            )


def _check_type(var_name: str, value: Any, dtype: Union[Tuple[type, type], type]) -> None:
    """
    Check key-value type.

    Parameters
    ----------
    var_name : str
        The variable name for which to check the type (used for error message)!
    value : Any
        The value for which to check the type.
    dtype : Union[Tuple[type, type], type]
        The expected data type of the `value`.

    Raises
    ------
    TypeError
        If the `value` type does not match the expected `dtype`.
    """

    if not isinstance(value, dtype):
        raise TypeError(
            f"'{var_name}' key-value is expected to be of type {dtype} but is {type(value)}!"
        )


def _find_value_type(content: dict) -> str:
    """
    Find the correct type of the content.

    Parameters
    ----------
    content : dict
        The content for which to find the appropriate data type.

    Returns
    -------
    str
        The correct data type.

    Raises
    ------
    ValueError
        If missing required fields.
    """

    value_type = ALL_VALUE_TYPES & set(content.keys())

    if len(value_type) == 0:
        raise ValueError(
            f"'value<TYPE>' field is either missing or incorrect: {content}. Valid values are: {VALUE_TYPES}."
        )
    if len(value_type) != 1:
        raise ValueError(f"Multiple fields 'value<TYPE>' are not supported: {content}")

    return value_type.pop()


def _move_clause_objects_to_str(objects: list) -> str:
    """
    _summary_

    Parameters
    ----------
    objects : list
        _description_

    Returns
    -------
    str
        _description_
    """

    to_return = " objects: ["
    for obj in objects:
        if "id" in obj:
            id_beacon = "id"
        else:
            id_beacon = "beacon"
        to_return += f"{{{id_beacon}: {dumps(obj[id_beacon])}}} "

    return to_return + "]"
