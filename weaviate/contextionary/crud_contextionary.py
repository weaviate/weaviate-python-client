"""
Contextionary class definition.
"""
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _decode_json_response_dict


class Contextionary:
    """
    Contextionary class used to add extend the Weaviate contextionary module
    or to get vector/s of a specific concept.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Contextionary class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        """

        self._connection = connection

    def extend(self, concept: str, definition: str, weight: float = 1.0) -> None:
        """
        Extend the text2vec-contextionary with new concepts

        Parameters
        ----------
        concept : str
            The new concept that should be added that is not in the Weaviate
            or needs to be updated, e.g. an abbreviation.
        definition : str
            The definition of the new concept.
        weight : float, optional
            The weight of the new definition compared to the old one,
            must be in-between the interval [0.0; 1.0], by default 1.0

        Examples
        --------
        >>> client.contextionary.extend(
        ...     concept = 'palantir',
        ...     definition = 'spherical stone objects used for communication in Middle-earth'
        ... )


        Raises
        ------
        TypeError
            If an argument is not of an appropriate type.
        ValueError
            If 'weight' is outside the interval [0.0; 1.0].
        requests.ConnectionError
            If text2vec-contextionary could not be extended.
        weaviate.UnexpectedStatusCodeException
            If the network connection to weaviate fails.
        """

        if not isinstance(concept, str):
            raise TypeError("Concept must be string")
        if not isinstance(definition, str):
            raise TypeError("Definition must be string")
        if not isinstance(weight, float):
            raise TypeError("Weight must be float")

        if weight > 1.0 or weight < 0.0:
            raise ValueError("Weight out of limits 0.0 <= weight <= 1.0")

        extension = {"concept": concept, "definition": definition, "weight": weight}

        try:
            response = self._connection.post(
                path="/modules/text2vec-contextionary/extensions",
                weaviate_object=extension,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "text2vec-contextionary could not be extended."
            ) from conn_err
        if response.status_code == 200:
            # Successfully extended
            return
        raise UnexpectedStatusCodeException("Extend text2vec-contextionary", response)

    def get_concept_vector(self, concept: str) -> dict:
        """
        Retrieves the vector representation of the given concept.

        Parameters
        ----------
        concept : str
            Concept for which the vector should be retrieved.
            May be camelCase for word combinations.

        Examples
        --------
        >>> client.contextionary.get_concept_vector('king')
        {
            "individualWords": [
                {
                "info": {
                    "nearestNeighbors": [
                    {
                        "word": "king"
                    },
                    {
                        "distance": 5.7498446,
                        "word": "kings"
                    },
                    ...,
                    {
                        "distance": 6.1396513,
                        "word": "queen"
                    }
                    ],
                    "vector": [
                    -0.68988,
                    ...,
                    -0.561865
                    ]
                },
                "present": true,
                "word": "king"
                }
            ]
        }

        Returns
        -------
        dict
            A dictionary containing info and the vector/s of the concept.
            The vector might be empty if the text2vec-contextionary does not contain it.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        path = "/modules/text2vec-contextionary/concepts/" + concept
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "text2vec-contextionary vector was not retrieved."
            ) from conn_err
        else:
            res = _decode_json_response_dict(response, "text2vec-contextionary vector")
            assert res is not None
            return res
