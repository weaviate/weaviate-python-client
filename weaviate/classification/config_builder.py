import sys
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.connect import REST_METHOD_POST
import time


class ConfigBuilder:

    def __init__(self, connection, classification):
        self._connection = connection
        self._classification = classification
        self.config = {}
        self.wait_for_completion = False

    def with_type(self, type):
        self.config["type"] = type
        return self

    def with_k(self, k):
        self.config["k"] = k
        return self

    def with_class_name(self, class_name):
        self.config["class"] = class_name
        return self

    def with_classify_properties(self, classify_properties):
        self.config["classifyProperties"] = classify_properties
        return self

    def with_based_on_properties(self, based_on_properties):
        self.config["basedOnProperties"] = based_on_properties
        return self

    def with_source_where_filter(self, filter):
        self.config["sourceWhere"] = filter
        return self

    def with_training_set_where_filter(self, filter):
        self.config["trainingSetWhere"] = filter
        return self

    def with_target_where_filter(self, filter):
        self.config["targetWhere"] = filter
        return self

    def with_wait_for_completion(self):
        self.wait_for_completion = True
        return self

    def _raise_missing_configuration_error(self, field):
        raise ValueError(f"{field} is not set for this classification")

    def _validate_config(self):
        required_fields = ["type", "class", "basedOnProperties", "classifyProperties"]
        for field in required_fields:
            if field not in self.config:
                self._raise_missing_configuration_error(field)

        if self.config["type"] == "knn":
            if "k" not in self.config:
                self._raise_missing_configuration_error("k")

    def _start(self):
        try:
            response = self._connection.run_rest("/classifications", REST_METHOD_POST, self.config)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, classification may not started.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 201:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("Start classification", response)

    def do(self):
        """ Start the classification.

        :return:
        """
        self._validate_config()

        response = self._start()
        if not self.wait_for_completion:
            return response

        # wait for completion
        classification_uuid = response["id"]
        while not self._classification.is_classification_complete(classification_uuid):
            time.sleep(2.0)
        return self._classification.get_classification_status(classification_uuid)
