import json


class Builder:

    def __init__(self, class_name, properties):
        self._class_name = class_name
        self._properties = properties
        self.filter = None



    def with_filter(self, filter):
        """

        :param filter:
        :return:
        """
        self.filter = Filter(filter)
        return self

    def do(self):
        """
        :return:
        """
        query = f'{{Get{{Things{{{self._class_name}'
        if self.filter is not None:
            query = query + '(where:' + str(self.filter)+')'
        query = query + f'{self._properties}}}}}}}'

        print(query)

class Get:
    def things(class_name, properties):
        return Builder(class_name, properties)


class Filter:

    def __init__(self, content):
        """

        :param content:
        :type content: dict
        """
        if not isinstance(content, dict):
            raise TypeError

        if "path" in content:
            self.is_filter = True
            self._parse_filter(content)
        elif "operator" in content:
            self.is_filter = False
            self._parse_operator(content)
        else:
            raise ValueError("Filter does not contain required fields")

    def _parse_filter(self, content):
        self.path = json.dumps(content["path"])
        self.operator = content["operator"]
        self.value_type = find_value_type(content)
        self.value = content[self.value_type]

    def _parse_operator(self, content):
        self.operator = content["operator"]
        self.operands = []
        for operand in content["operands"]:
            self.operands.append(Filter(operand))

    def __str__(self):
        if self.is_filter:
            return f'{{\
            path: {self.path} \
            operator: {self.operator} \
            {self.value_type}: "{self.value}"}}'
        else:
            operands_str = []
            for operand in self.operands:
                operands_str.append(str(operand))

            operands = ", ".join(operands_str)

            return f'{{\
            operator: {self.operator} \
            operands: [{operands}] \
            }}'


def find_value_type(content):
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
        raise ValueError("Where no valid value type found")
