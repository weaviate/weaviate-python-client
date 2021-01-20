import sys
import time
from typing import Dict, Any
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from weaviate.connect import REST_METHOD_POST, Connection


class ConfigBuilder:
    """
    ConfigBuild class that is used to configure a classification process.
    """

    def __init__(self, connection: Connection, classification: 'Classification'):
        """
        Initialize a ConfiBuilder class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        classification : weaviate.classification.Classification
            Classification object to be configured using this ConfigBuilder
            instance.
        """

        self._connection = connection
        self._classification = classification
        self._config: Dict[str, Any] = {}
        self._wait_for_completion = False

    def with_type(self, type: str) -> 'ConfigBuilder':
        """
        Set classification type.

        Parameters
        ----------
        type : str
            Type of the desired classification.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        self._config["type"] = type
        return self

    def with_k(self, k: int) -> 'ConfigBuilder':
        """
        Set k number for the kNN.

        Parameters
        ----------
        k : int
            Number of objects to use to make a classification guess.
            (For kNN)

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        self._config["settings"] = {
            "k" : k
        }
        return self

    def with_class_name(self, class_name: str) -> 'ConfigBuilder':
        """
        What Object type to classify.

        Parameters
        ----------
        class_name : str
            Name of the class to be classified.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        self._config["class"] = class_name
        return self

    def with_classify_properties(self, classify_properties: list) -> 'ConfigBuilder':
        """
        Set the classify properties.

        Parameters
        ----------
        classify_properties: list
            A list of properties to clasify.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        self._config["classifyProperties"] = classify_properties
        return self

    def with_based_on_properties(self, based_on_properties: list) -> 'ConfigBuilder':
        """
        Set properties to build the classification on.

        Parameters
        ----------
        based_on_properties: list
            A list of properties to classify on.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        self._config["basedOnProperties"] = based_on_properties
        return self

    def with_source_where_filter(self, filter: dict) -> 'ConfigBuilder':
        """
        Set Source 'where' Filter.

        Parameters
        ----------
        filter : dict
            Filter to use, as a dict.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        if "filters" not in self._config:
            self._config["filters"] = {}
        self._config["filters"]["sourceWhere"] = filter
        return self

    def with_training_set_where_filter(self, filter: dict) -> 'ConfigBuilder':
        """
        Set Training set 'where' Filter.

        Parameters
        ----------
        filter : dict
            Filter to use, as a dict.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        if "filters" not in self._config:
            self._config["filters"] = {}
        self._config["filters"]["trainingSetWhere"] = filter
        return self

    def with_target_where_filter(self, filter: dict) -> 'ConfigBuilder':
        """
        Set Target 'where' Filter.

        Parameters
        ----------
        filter : dict
            Filter to use, as a dict.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        if "filters" not in self._config:
            self._config["filters"] = {}
        self._config["filters"]["targetWhere"] = filter
        return self

    def with_wait_for_completion(self) -> 'ConfigBuilder':
        """
        Wait for completion.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        self._wait_for_completion = True
        return self

    def with_settings(self, settings: dict) -> 'ConfigBuilder':
        """
        Set settings for the classification. NOTE if you are using 'kNN'
        the value 'k' can be set by this method or by 'with_k'.
        This method overwrites any previously set settings, like 'k' from
        the 'with_k' method.

        Parameters
        ----------
        settings: dict
            Additional settings to be set/overwritten.

        Returns
        -------
        ConfigBuilder
            Updated ConfigBuilder.
        """

        self._config["settings"] = settings
        return self

    def _validate_config(self) -> None:
        """
        Validate the current classification configuration.

        Raises
        ------
        ValueError
            If a mandatory field is not set.
        """

        required_fields = ["type", "class", "basedOnProperties", "classifyProperties"]
        for field in required_fields:
            if field not in self._config:
                raise ValueError(f"{field} is not set for this classification")

        if "settings" in self._config:
            if not isinstance(self._config["settings"], dict):
                raise TypeError('"settings" should be of type dict')

        if self._config["type"] == "knn":
            if "k" not in self._config.get("settings", []):
                raise ValueError("k is not set for this classification")

    def _start(self) -> dict:
        """
        Start the classification based on the configuration set.

        Returns
        -------
        dict
            Classification result.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            Unexpected error.
        """

        try:
            response = self._connection.run_rest("/classifications", REST_METHOD_POST, self._config)
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                        + ' Connection error, classification may not started.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 201:
            return response.json()
        raise UnexpectedStatusCodeException("Start classification", response)

    def do(self) -> dict:
        """
        Start the classification.

        Returns
        -------
        dict
            Classification result.
        """

        self._validate_config()

        response = self._start()
        if not self._wait_for_completion:
            return response

        # wait for completion
        classification_uuid = response["id"]
        #print(classification_uuid)
        while self._classification.is_running(classification_uuid):
            time.sleep(2.0)
        return self._classification.get(classification_uuid)
