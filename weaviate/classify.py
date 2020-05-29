from .exceptions import UnexpectedStatusCodeException
from .connect import REST_METHOD_POST, REST_METHOD_GET
import sys
import validators
import copy

SOURCE_WHERE_FILTER = 0
TRAINING_SET_WHERE_FILTER = 1
TARGET_WHERE_FILTER = 2


class Classification:

    def __init__(self, connection):
        self._connection = connection

    def start(self, config):
        """ Start the classification described by the config on weaviate and return the status.
            Does not block or wait until the classification is complete.

        :param config: for the classification.
                       A config can be created using get_contextual_config or get_knn_config.
        :return: the weaviate response if successfully started or an Exception.
        """

        try:
            response = self._connection.run_rest("/classifications", REST_METHOD_POST, config)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, classification may not started.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 201:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Start classification", response)

    def add_filter_to_config(self, filter_type, filter, config):
        """ Create a new config based on the provided with the added filter.

        :param filter_type: May be any of the filter type constants such as
                            SOURCE_WHERE_FILTER, TRAINING_SET_WHERE or TARGET_WHERE.
        :type filter_type: int in form of constant (enum)
        :param filter: The gql filter to be used.
        :type filter: dict
        :param config: The config on which the filter should be applied.
        :param config: dict
        :return: A new copy of the config including the filter.
        """
        if not isinstance(filter_type, int):
            raise TypeError("Please choose a constant e.g. weaviate.TRAINING_SET_WHERE_FILTER")
        if not isinstance(filter, dict):
            raise TypeError("Filter must be a dict containing a GQL filter")
        if not isinstance(config, dict):
            raise TypeError("Not a valid config")

        new_config = copy.deepcopy(config)
        if filter_type == SOURCE_WHERE_FILTER:
            new_config["sourceWhere"] = filter
        elif filter_type == TRAINING_SET_WHERE_FILTER:
            new_config["trainingSetWhere"] = filter
        elif filter_type == TARGET_WHERE_FILTER:
            new_config["targetWhere"] = filter
        else:
            raise ValueError("No valid filter set use constants e.g. weaviate.TRAINING_SET_WHERE_FILTER")

        return new_config

    def get_knn_config(self, schema_class_name, k, based_on_properties, classify_properties):
        """ Create a configuration to be used for a knn classification

        :param schema_class_name: Class on which the classification is executed.
        :type schema_class_name: str
        :param k: the number of nearest neighbours that are taken into account for the classification.
        :type k: int
        :param based_on_properties: The property or the properties that are used to for the classification.
                                    This field is compared to the other fields and serves as the decision base.
        :type based_on_properties: str, list of str
        :param classify_properties: The property or the properties that are labeled (the classes).
        :type classify_properties: str, list of str
        :return: A configuration to be used to start a classification
        :raises:
            TypeError: if argument is of wrong type.
            ValueError: if argument contains invalid values.
        """


        if not isinstance(schema_class_name, str):
            raise TypeError("Schema class name must be of type string")
        if not isinstance(k, int):
            raise TypeError("K must be of type integer")
        if isinstance(based_on_properties, str):
            based_on_properties = [based_on_properties]
        if isinstance(classify_properties, str):
            classify_properties = [classify_properties]
        if not isinstance(based_on_properties, list):
            raise TypeError("Based on properties must be of type string or list of strings")
        if not isinstance(classify_properties, list):
            raise TypeError("Classify properties must be of type string or list of strings")
        if k <= 0:
            raise ValueError("K must must take a value >= 1")

        config = {
            "class": schema_class_name,
            "k": k,
            "basedOnProperties": based_on_properties,
            "classifyProperties": classify_properties,
            "type": "knn"
        }

        return config

    def get_contextual_config(self, schema_class_name, based_on_properties, classify_properties):
        """ Create a configuration to start a contextual classification

        :param schema_class_name: Class on which the classification is executed.
        :type schema_class_name: str
        :param based_on_properties: The property or the properties that are used to for the classification.
                                    This field is compared to the other fields and serves as the decision base.
        :type based_on_properties:  str, list of str
        :param classify_properties: The property or the properties that are labeled (the classes).
        :type classify_properties: str, list of str
        :return: A config that can be used to start a classification
        :raises:
            TypeError: if argument is of wrong type.
        """

        if not isinstance(schema_class_name, str):
            raise TypeError("Schema class name must be of type string")
        if isinstance(based_on_properties, str):
            based_on_properties = [based_on_properties]
        if isinstance(classify_properties, str):
            classify_properties = [classify_properties]
        if not isinstance(based_on_properties, list):
            raise TypeError("Based on properties must be of type string or list of strings")
        if not isinstance(classify_properties, list):
            raise TypeError("Classify properties must be of type string or list of strings")

        config = {
            "class": schema_class_name,
            "basedOnProperties": based_on_properties,
            "classifyProperties": classify_properties,
            "type": "contextual"
        }

        return config

    def get_classification_status(self, classification_uuid):
        """ Polls the current state of the given classification

        :param classification_uuid: identifier of the classification.
        :type classification_uuid: str
        :return: a dict containing the weaviate answer.
        :raises:
            ValueError: if not a proper uuid.
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """

        if not validators.uuid(classification_uuid):
            raise ValueError("Given UUID does not have a proper form")

        try:
            response = self._connection.run_rest("/classifications/" + classification_uuid, REST_METHOD_GET)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, classification status could not be retrieved.'
                                 ).with_traceback(
                sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Get classification status", response)

    def is_classification_complete(self, classification_uuid):
        """ Checks if a previously started classification job has completed.

        :param classification_uuid: identifier of the classification.
        :return: true if given classification has finished.
        """
        try:
            response = self.get_classification_status(classification_uuid)
        except ConnectionError:
            return False
        if response["status"] == "completed":
            return True
        return False