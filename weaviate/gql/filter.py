"""
GraphQL filters for `Get` and `Aggregate` commands.
GraphQL abstract class for GraphQL commands to inherit from.
"""
import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from json import dumps
from typing import Any, Union

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.error_msgs import FILTER_BEACON_V14_CLS_NS_W
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import get_vector


class GraphQL(ABC):
    """
    A base abstract class for GraphQL commands, such as Get, Aggregate.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a GraphQL abstract class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection

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

    def do(self) -> dict:
        """
        Builds and runs the query.

        Returns
        -------
        dict
            The response of the query.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        query = self.build()

        try:
            response = self._connection.post(path="/graphql", weaviate_object={"query": query})
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Query was not successful.") from conn_err
        if response.status_code == 200:
            return response.json()  # success
        raise UnexpectedStatusCodeException("Query was not successful", response)


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

    def __str__(self):
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

    def __str__(self):
        near_vector = f'nearVector: {{vector: {dumps(self._content["vector"])}'
        if "certainty" in self._content:
            near_vector += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            near_vector += f' distance: {self._content["distance"]}'
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

    def __str__(self):

        near_object = f'nearObject: {{{self.obj_id}: "{self._content[self.obj_id]}"'
        if "certainty" in self._content:
            near_object += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            near_object += f' distance: {self._content["distance"]}'
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

    def __str__(self):
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


class NearImage(Filter):
    """
    NearObject class used to filter weaviate objects.
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

        super().__init__(content)

        if "image" not in self._content:
            raise ValueError('"content" is missing the mandatory key "image"!')

        _check_type(var_name="image", value=self._content["image"], dtype=str)
        if "certainty" in self._content:
            if "distance" in self._content:
                raise ValueError(
                    "Cannot have both 'certainty' and 'distance' at the same time. "
                    "Only one is accepted."
                )
            _check_type(var_name="certainty", value=self._content["certainty"], dtype=float)
        if "distance" in self._content:
            _check_type(var_name="distance", value=self._content["distance"], dtype=float)

    def __str__(self):
        near_image = f'nearImage: {{image: "{self._content["image"]}"'
        if "certainty" in self._content:
            near_image += f' certainty: {self._content["certainty"]}'
        if "distance" in self._content:
            near_image += f' distance: {self._content["distance"]}'
        return near_image + "} "


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

        self.path = dumps(content["path"])
        self.operator = content["operator"]
        self.value_type = _find_value_type(content)
        self.value = content[self.value_type]

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
        _content = deepcopy(content)
        self.operator = _content["operator"]
        self.operands = []
        for operand in _content["operands"]:
            self.operands.append(Where(operand))

    def __str__(self):
        if self.is_filter:
            gql = f"where: {{path: {self.path} operator: {self.operator} {self.value_type}: "
            if self.value_type in ["valueInt", "valueNumber"]:
                gql += f"{self.value}}}"
            elif self.value_type == "valueBoolean":
                gql += f"{_bool_to_str(self.value)}}}"
            elif self.value_type == "valueGeoRange":
                gql += f"{dumps(self.value)}}}"
            else:
                gql += f'"{self.value}"}}'
            return gql + " "

        operands_str = []
        for operand in self.operands:
            # remove the `where: ` from the operands and the last space
            operands_str.append(str(operand)[7:-1])
        operands = ", ".join(operands_str)
        return f"where: {{operator: {self.operator} operands: [{operands}]}} "


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


def _check_direction_clause(direction: dict) -> dict:
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


def _check_type(var_name: str, value: Any, dtype: type) -> None:
    """
    Check key-value type.

    Parameters
    ----------
    var_name : str
        The variable name for which to check the type (used for error message)!
    value : Any
        The value for which to check the type.
    dtype : type
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

    if "valueString" in content:
        to_return = "valueString"
    elif "valueText" in content:
        to_return = "valueText"
    elif "valueInt" in content:
        to_return = "valueInt"
    elif "valueNumber" in content:
        to_return = "valueNumber"
    elif "valueDate" in content:
        to_return = "valueDate"
    elif "valueBoolean" in content:
        to_return = "valueBoolean"
    elif "valueGeoRange" in content:
        to_return = "valueGeoRange"
    else:
        raise ValueError(f"Filter is missing required fields: {content}")
    return to_return


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
