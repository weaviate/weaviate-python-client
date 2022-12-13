from typing import Union, Callable, Optional
from unittest.mock import Mock


def mock_connection_func(
    rest_method: Optional[str] = None,
    return_json: Union[list, dict, None] = None,
    status_code: int = 200,
    side_effect: Union[Exception, Callable, None] = None,
    connection_mock: Optional[Mock] = None,
    server_version: str = "1.13.2,",
    timeout_config: tuple = (10, 60),
) -> Mock:
    """
    Mock the Connection class and mocking its public method/s.

    Parameters
    ----------
    rest_method : str
        The REST method to mock, accepted values: 'delete', 'post', 'put', 'patch' and 'get'.
        NOTE: It is case insensitive.
    return_json : [Union[list, dict, None], optional
        The return value of the `.json()` method on the response of the `rest_method` method.
        By default None.
    status_code : int, optional
        The code the `rest_method` should return, by default 200.
    side_effect : Union[Exception, Callable, None], optional
        The side effect of the `rest_method`. If `side_effect` is not None the other arguments are
        not used, by default None.
    connection_mock : Optional[Mock], optional
        The already mocked Connection object to add on top a new mocked method or to overwrite an
        existing one. If None start from a new mocked Connection, by default None.

    Returns
    -------
    Mock
        The mocked Connection object.

    Raises
    ------
    ValueError
        If `rest_method` does not have an accepted value.
    """

    if connection_mock is None:
        connection_mock = Mock()

    if rest_method:
        if rest_method.lower() == "delete":
            rest_method_mock = connection_mock.delete
        elif rest_method.lower() == "post":
            rest_method_mock = connection_mock.post
        elif rest_method.lower() == "put":
            rest_method_mock = connection_mock.put
        elif rest_method.lower() == "patch":
            rest_method_mock = connection_mock.patch
        elif rest_method.lower() == "get":
            rest_method_mock = connection_mock.get
        elif rest_method.lower() == "head":
            rest_method_mock = connection_mock.head
        else:
            raise ValueError(
                "Wrong value for `rest_method`! Accepted values: 'delete', 'post', 'put', 'patch', "
                f"'get' and 'head', but got: {rest_method}"
            )

        if side_effect is None:
            # Create mock
            rest_method_return_mock = Mock()
            # mock the json() method and set its return value
            rest_method_return_mock.json.return_value = return_json
            # Set status code
            rest_method_return_mock.configure_mock(status_code=status_code)
            # set the return value of the given REST method
            rest_method_mock.return_value = rest_method_return_mock
        else:
            # set the side effect for the given REST method
            rest_method_mock.side_effect = side_effect

    connection_mock.server_version = server_version
    connection_mock.timeout_config = timeout_config
    connection_mock._timeout_config = timeout_config
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
