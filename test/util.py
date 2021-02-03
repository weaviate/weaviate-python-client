from unittest.mock import Mock
import weaviate


def replace_connection(client, connection):
    """
    Replace connection with a mocked one.

    Parameters
    ----------
    weaviate : weaviate.Client
        The weaviate client object for which to mock connection.
    connection : unittest.mock.Mock
        The mock connection.
    """

    client._connection = connection
    client.classification._connection = connection
    client.schema._connection = connection
    client.schema.property._connection = connection
    client.contextionary._connection = connection
    client.batch._connection = connection
    client.data_object._connection = connection
    client.data_object.reference._connection = connection
    client.query._connection = connection


def mock_run_rest(return_json=None, status_code=200, side_effect=None) -> Mock:
    """
    Mock `run_rest` call, i.e. the `.json()` return value, the `status_code` attribute
    and also the raised exception when called.

    Parameters
    ----------
    mock : unittest.mock.Mock
        The mock to add the method to (this is call by reference
        so this object will be edited).
    return_json : any
        The return value of the `.json()` method.
    status_code : int
        The code it should return.
    side_effect : Exception()
        An instance of an exception to be raised when the `run_rest` is called.
        If side_effect is provided the other arguments are not used.

    Returns
    -------
    unittest.mock.Mock
        The mock object for the `run_rest`.
    """

    connection_mock = Mock()    
    if side_effect is not None:
        connection_mock.run_rest.side_effect = side_effect
    else: 
        # Create mock
        return_value_mock = Mock()
        # mock the json() method and set its return value
        return_value_mock.json.return_value = return_json
        # Set status code
        return_value_mock.configure_mock(status_code=status_code)
        # Add the return value to the given mock
        # set return object to mock object
        connection_mock.run_rest.return_value = return_value_mock 

    return connection_mock


def check_error_message(self, error, message):
    """
    Check if 'error' message equal 'message'.

    Parameters
    ----------
    error : unittest.case._AssertRaisesContext
        Unittest assertion error
    message : str
        Expected message.
    """

    self.assertEqual(str(error.exception), message)


def check_startswith_error_message(self, error, message):
    """
    Check if 'error' message equal 'message'.

    Parameters
    ----------
    error : unittest.case._AssertRaisesContext
        Unittest assertion error
    message : str
        Expected start of the error message.
    """

    self.assertTrue(str(error.exception).startswith(message))
