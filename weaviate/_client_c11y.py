import sys
from .exceptions import *
from weaviate.connect import REST_METHOD_POST, REST_METHOD_GET


def _extend_c11y(self, concept, definition, weight=1.0):
    """ Extend the c11y with new concepts

    :param concept: The new concept that should be added, e.g. an abbreviation.
    :type concept: str
    :param definition: The definition of the new concept.
    :type definition: str
    :param weight: The weight of the new definition compared to the old one.
    :type weight: float
    :return: None if successful
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
        response = self._connection.run_rest("/c11y/extensions/", REST_METHOD_POST, extension)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err)
                             + ' Connection error, c11y could not be extended.'
                             ).with_traceback(
            sys.exc_info()[2])

    if response.status_code == 200:
        return  # Successfully extended
    else:
        raise UnexpectedStatusCodeException("Extend c11y", response)


def _get_c11y_vector(self, word):
    """ Retrieves the vector representation of the given word.

    :param word: for which the vector should be retrieved. May be CamelCase for word combinations.
    :type word: str
    :return: the vector or vectors of the given word.
        The vector might be empty if the c11y does not contain it.
    :raises:
        AttributeError:
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """

    path = "/c11y/words/" + word
    try:
        response = self._connection.run_rest(path, REST_METHOD_GET)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err)
                             + ' Connection error, c11y vector was not retrieved.').with_traceback(
            sys.exc_info()[2])
    except AttributeError:
        raise
    except Exception as e:
        raise type(e)(
            str(e) + ' Unexpected exception please report this excetpion in an issue.').with_traceback(
            sys.exc_info()[2])
    else:
        if response.status_code == 200:
            return response.json()
        else:
            raise UnexpectedStatusCodeException("C11y vector", response)


