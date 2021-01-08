import requests
from unittest.mock import Mock



def add_run_rest_to_mock(mock, return_json=None, status_code=200):
    """Adds the run_rest method to a mock using the given options

    :param mock: the mock to add the method to (this is call by reference so this object will be edited)
    :param return_json: the json it should return
    :param status_code: the code it should return
    :return: returns the same mock as given. The object is not copied so the usage of the return value is not necessary
    """
    # Create mock
    return_value_mock = Mock()
    # set the json
    return_value_mock.json.return_value = return_json
    # Set status code
    return_value_mock.configure_mock(status_code=status_code)

    # Add the return value to the given mock
    mock.run_rest.return_value = return_value_mock  # set return object to mock object

    return mock


def run_rest_raise_connection_error(path, rest_method, weaviate_object=None, retries=3, params={}):
    """ A mock that no mather the input will throw an ConnectionError

    :raises ConnectionError
    """
    raise requests.exceptions.ConnectionError


def replace_connection(weaviate, connection):
    """

    :param weaviate:
    :type weaviate: weaviate.Client
    :param connection:
    :type connection: weaviate.connection.Connection
    :return:
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