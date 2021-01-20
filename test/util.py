import requests
from unittest.mock import Mock



def add_run_rest_to_mock(mock, return_json=None, status_code=200):
    """
    Adds the run_rest method to a mock using the given options.

    Parameters
    ----------
    mock : unittest.mock.Mock
        The mock to add the method to (this is call by reference
        so this object will be edited).
    return_json : any
        The return value of the `.json()` method.
    status_code : int
        The code it should return.

    Returns
    -------
    unittest.mock.Mock
        The same mock as given. The object is not copied so the
        usage of the return value is not necessary,
    """
    # Create mock
    return_value_mock = Mock()
    # set the json
    return_value_mock.json.return_value = return_json
    # Set status code
    return_value_mock.configure_mock(status_code=status_code)
    # Add the return value to the given mock
    # set return object to mock object
    mock.run_rest.return_value = return_value_mock 

    return mock


def run_rest_raise_connection_error(path, rest_method, weaviate_object=None, retries=3, params={}):
    """
    A mock that no mather the input will throw an ConnectionError.

    Raises
    ------
    requests.exceptions.ConnectionError
    """
    raise requests.exceptions.ConnectionError


def replace_connection(weaviate, connection):
    """
    Replace connection with a mocked one.

    Parameters
    ----------
    weaviate : weaviate.Client
        The weaviate client object for which to mock connection.
    connection : unittest.mock.Mock
        The mock connection.
    """

    weaviate._connection = connection
    weaviate.classification._connection = connection
    weaviate.schema._connection = connection
    weaviate.schema.property._connection = connection
    weaviate.contextionary._connection = connection
    weaviate.batch._connection = connection
    weaviate.data_object._connection = connection
    weaviate.data_object.reference._connection = connection
    weaviate.query._connection = connection
