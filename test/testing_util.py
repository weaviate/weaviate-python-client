from unittest.mock import Mock

#Adds the run_rest method to a mock using the given options
def add_run_rest_to_mock(mock, return_json=None, status_code=200):
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
    raise ConnectionError