import sys
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.connect import REST_METHOD_POST, REST_METHOD_GET, Connection


class Contextionary:
    """
    Contextionary class used to add exted the weaviate contextionary module
    or to get vector/s of a specific concept.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Contextionary class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection

    def extend(self,
            concept: str,
            definition: str,
            weight: float=1.0
        ) -> None:
        """
        Extend the text2vec-contextionary with new concepts

        Parameters
        ----------
        concept : str
            The new concept that should be added that is not in the weaviate
            or needs to be updated, e.g. an abbreviation.
        definition : str
            The definition of the new concept.
        weight : float, optional
            The weight of the new definition compared to the old one,
            must be inbetween the interval [0.0; 1.0], by default 1.0

        Raises
        ------
        TypeError
            If an argument is not of an approptiate type.
        ValueError
            If 'weight' is outside the interval [0.0; 1.0].
        requests.exceptions.ConnectionError
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

        extension = {
            "concept": concept,
            "definition": definition,
            "weight": weight
        }

        try:
            response = self._connection.run_rest(
                "/modules/text2vec-contextionary/extensions",
                REST_METHOD_POST,
                extension
                )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, text2vec-contextionary could not be extended.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
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
            May be CamelCase for word combinations.

        Returns
        -------
        dict
            A dictionary containing info and the vector/s of the concept.
            The vector might be empty if the text2vec-contextionary does not contain it.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        Exception
            Unexpected exception that should be reported in an issue.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        AttributeError
        """

        path = "/modules/text2vec-contextionary/concepts/" + concept
        try:
            response = self._connection.run_rest(path, REST_METHOD_GET)
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, text2vec-contextionary vector was not retrieved.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        except AttributeError:
            raise
        except Exception as error:
            message = str(error)\
                    + ' Unexpected exception please report this excetpion in an issue.'
            raise type(error)(message).with_traceback(sys.exc_info()[2])
        else:
            if response.status_code == 200:
                return response.json()
            raise UnexpectedStatusCodeException("text2vec-contextionary vector", response)
