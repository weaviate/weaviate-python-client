import json


class Explore:

    def __init__(self, content):
        """

        :param content: of the explore clause
        """
        if not isinstance(content, dict):
            raise TypeError(f"Explore filter is expected to be type dict but was {type(content)}")

        self.concepts = _check_concept(content)
        self.certainty = None
        self.move_to = None
        self.move_away_from = None

        if "certainty" in content:
            if not isinstance(content["certainty"], float):
                raise TypeError(f"certainty is expected to be a float but was {type(content['certainty'])}")

            self.certainty = content["certainty"]

        if "moveTo" in content:
            self.move_to = _check_direction_clause(content["moveTo"])

        if "moveAwayFrom" in content:
            self.move_away_from = _check_direction_clause(content["moveAwayFrom"])


    def __str__(self):
        explore = f'{{concepts: {json.dumps(self.concepts)} '
        if self.certainty is not None:
            explore += f'certainty: {str(self.certainty)} '
        if self.move_to is not None:
            explore += f'moveTo:{{concepts: {json.dumps(self.move_to["concepts"])} force: {self.move_to["force"]}}} '
        if self.move_away_from is not None:
            explore += f'moveAwayFrom:{{concepts: {json.dumps(self.move_away_from["concepts"])} force: {self.move_away_from["force"]}}} '
        return explore + '}'

def _check_direction_clause(direction):
    """ Validate the direction sub clause

    :param direction:
    :return:
    """
    if not isinstance(direction, dict):
        raise TypeError(f"move clause should be dict but was {type(direction)}")
    _check_concept(direction)
    if not "force" in direction:
        raise ValueError("move clause needs to state a force")
    if not isinstance(direction["force"], float):
        raise TypeError(f"force should be float but was {type(direction['force'])}")
    return direction

def _check_concept(content):
    if "concepts" not in content:
        raise ValueError("No concepts in content")

    if not isinstance(content["concepts"], (list, str)):
        raise ValueError(f"Concepts must be of type list or str not {type(content['concepts'])}")
    return content["concepts"]


class WhereFilter:

    def __init__(self, content):
        """

        :param content: dict describing the filter.
        :type content: dict
        :raises:
            KeyError: If a mandatory key is missing in the filter content
        """
        if not isinstance(content, dict):
            raise TypeError

        if "path" in content:
            self.is_filter = True
            self._parse_filter(content)
        elif "operands" in content:
            self.is_filter = False
            self._parse_operator(content)
        else:
            self._raise_filter_misses_fields(content)

    def _raise_filter_misses_fields(self, content):
        raise ValueError("Filter is missing required fileds: ", content)

    def _parse_filter(self, content):
        if "operator" not in content:
            self._raise_filter_misses_fields(content)

        self.path = json.dumps(content["path"])
        self.operator = content["operator"]
        self.value_type = self._find_value_type(content)
        self.value = content[self.value_type]

    def _parse_operator(self, content):
        if "operator" not in content:
            self._raise_filter_misses_fields(content)

        self.operator = content["operator"]
        self.operands = []
        for operand in content["operands"]:
            self.operands.append(WhereFilter(operand))

    def __str__(self):
        if self.is_filter:
            return f'{{path: {self.path} operator: {self.operator} {self.value_type}: "{self.value}"}}'
        else:
            operands_str = []
            for operand in self.operands:
                operands_str.append(str(operand))

            operands = ", ".join(operands_str)

            return f'{{operator: {self.operator} operands: [{operands}]}}'

    def _find_value_type(self, content):
        """

        :param content:
        :type content: dict
        :return:
        """
        if "valueString" in content:
            return "valueString"
        elif "valueText" in content:
            return "valueText"
        elif "valueInt" in content:
            return "valueInt"
        elif "valueNumber" in content:
            return "valueNumber"
        elif "valueDate" in content:
            return "valueDate"
        elif "valueBoolean" in content:
            return "valueBoolean"
        elif "valueGeoRange" in content:
            return "valueGeoRange"
        else:
            self._raise_filter_misses_fields(content)
