import sys
from typing import Union, Optional, List
import validators
from requests import Response
from weaviate.connect import REST_METHOD_POST
from weaviate.connect import REST_METHOD_PATCH
from weaviate.connect import REST_METHOD_PUT
from weaviate.connect import REST_METHOD_GET
from weaviate.connect import REST_METHOD_DELETE
from weaviate.connect import Connection
from weaviate.exceptions import ObjectAlreadyExistsException
from weaviate.exceptions import RequestsConnectionError
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _get_dict_from_object
from weaviate.data.references import Reference


class DataObject:
    """
    DataObject class used to manipulate object to/from weaviate.
    """
    def __init__(self, connection: Connection):
        """
        Initialize a DataObject class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection
        self.reference = Reference(self._connection)

    def create(self,
            data_object: Union[dict, str],
            class_name: str,
            uuid: str=None,
            vector_weights: dict=None
        ) -> str:
        """
        Takes a dict describing the object and adds it to weaviate.

        Parameters
        ----------
        data_object : dict or str
            Object to be added.
            If type is str it should be either an URL or a file.
        class_name : str
            Class name associated with the object given.
        uuid : str, optional
            Object will be created under this uuid if it is provided.
            Otherwise weaviate will generate a uuid for this object,
            by default None.
        vector_weights : dict, optional
            Influence the weight of words on object creation.
            Default is None for no influence.

        Returns
        -------
        str
            Returns the UUID of the created object if successful.

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        weaviate.ObjectAlreadyExistsException
            If an object with the given uuid already exists within weaviate.
        weaviate.UnexpectedStatusCodeException
            If creating the object in weavate failed with a different reason,
            more information is given in the exception.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        """

        loaded_data_object = _get_dict_from_object(data_object)
        if not isinstance(class_name, str):
            raise TypeError("Expected class_name of type str but was: "\
                            + str(type(class_name)))

        weaviate_obj = {
            "class": class_name,
            "properties": loaded_data_object
        }
        if uuid is not None:
            if not isinstance(uuid, str):
                raise TypeError("Expected uuid to be of type str but was: "\
                                + str(type(uuid)))
            if not validators.uuid(uuid):
                raise ValueError("Given uuid does not have a valid form")

            weaviate_obj["id"] = uuid

        if vector_weights is not None:
            if not isinstance(vector_weights, dict):
                raise TypeError("Expected vector_weights to be of type dict but was "\
                                + str(type(vector_weights)))

            weaviate_obj["vectorWeights"] = vector_weights

        path = "/objects"
        try:
            response = self._connection.run_rest(path, REST_METHOD_POST, weaviate_obj)
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, object was not added to weaviate.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])

        if response.status_code == 200:
            return str(response.json()["id"])

        object_does_already_exist = False
        try:
            if 'already exists' in response.json()['error'][0]['message']:
                object_does_already_exist = True
        except KeyError:
            pass
        except Exception as error:
            message = str(error)\
                    + ' Unexpected exception please report this excetpion in an issue.'
            raise type(error)(message).with_traceback(sys.exc_info()[2])

        if object_does_already_exist:
            raise ObjectAlreadyExistsException(str(uuid))
        raise UnexpectedStatusCodeException("Creating object", response)

    def merge(self,
            data_object: Union[dict, str],
            class_name: str,
            uuid: str
        ) -> None:
        """
        Merge the given object with the already existing object in weaviate.
        Overwrites all given fields.

        Parameters
        ----------
        data_object : dict or str
            The object states the fields that should be updated.
            Fields not stated by object will not be changed.
            Fields that are None will not be changed.
            If type is str it should be either an URL or a file.
        class_name : str
            The class name of the object.
        uuid : str
            The ID of the object that should be changed.

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none successful status.
        """

        object_dict = _get_dict_from_object(data_object)

        if not isinstance(class_name, str):
            raise TypeError("Class must be type str")
        if not isinstance(uuid, str):
            raise TypeError("UUID must be type str")
        if not validators.uuid(uuid):
            raise ValueError("Not a proper UUID")

        payload = {
            "id": uuid,
            "class": class_name,
            "properties": object_dict
        }

        path = f"/objects/{uuid}"

        try:
            response = self._connection.run_rest(path, REST_METHOD_PATCH, payload)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, object was not patched.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 204:
            # Successful merge
            return
        raise UnexpectedStatusCodeException("PATCH merge of object not successful", response)

    def update(self,
            data_object: Union[dict, str],
            class_name: str,
            uuid: str
        ) -> None:
        """
        Update an already existing object with the given data object.
        Does not keep unset values.

        Parameters
        ----------
        data_object : dict or str
            Describes the new values. It may be an URL or path to a json
            or a python dict describing the new values.
        class_name : str
            Name of the class of the object that should be updated.
        uuid : str
            The UUID of the object that should be changed.

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        parsed_object = _get_dict_from_object(data_object)

        weaviate_obj = {
            "id": uuid,
            "class": class_name,
            "properties": parsed_object
        }

        path = f"/objects/{uuid}"
        try:
            response = self._connection.run_rest(path, REST_METHOD_PUT, weaviate_obj)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, object was not updated.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 200:
            # Successful update
            return
        raise UnexpectedStatusCodeException("Update object", response)

    def get_by_id(self,
            uuid: str,
            additional_properties: List[str]=None,
            with_vector: bool=False
        ) -> Optional[dict]:
        """
        Get an object as dict.

        Parameters
        ----------
        uuid : str
            The identifier of the object that should be retrieved.
        additional_properties : list of str, optional
            List of additional properties that should be included in the request,
            by default None
        with_vector: bool
            If True the `vector` property will be returned too,
            by default False.

        Returns
        -------
        dict or None
            dict in case the object exists.
            None in case the object does not exist.

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        response = self._get_object_response(uuid, additional_properties, with_vector)

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Get object", response)

    def get(self,
            additional_properties: List[str]=None,
            with_vector: bool=False
        ) -> List[dict]:
        """
        Gets all objects.

        Parameters
        ----------
        additional_properties : list of str, optional
            list of additional properties that should be included in the request,
            by default None
        with_vector: bool
            If True the `vector` property will be returned too,
            by default False.

        Returns
        -------
        list of dicts
            A list of all objects. If no objects where found the list is empty.

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        params = _get_params(additional_properties, with_vector)

        path = "/objects"

        try:
            response = self._connection.run_rest(path, REST_METHOD_GET, params=params)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error when getting objects'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException("Get object", response)

    def _get_object_response(self,
            object_uuid: str,
            additional_properties: List[str],
            with_vector: bool
        ) -> Response:
        """
        Retrieve an object from weaviate.

        Parameters
        ----------
        object_uuid : str
            The identifier of the object that should be retrieved.
        additional_properties : list of str, optional
            Defines the additional properties that should be included in the result.
        with_vector: bool
            If True the `vector` property will be returned too.

        Returns
        -------
        requests.Response
            Respose object.

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        """

        params = _get_params(additional_properties, with_vector)

        if not isinstance(object_uuid, str):
            object_uuid = str(object_uuid)
        try:
            response = self._connection.run_rest(
                "/objects/" + object_uuid,
                REST_METHOD_GET,
                params=params
                )
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error not sure if object exists'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        return response

    def delete(self, uuid: str) -> None:
        """
        Delete an existing object from weaviate.

        Parameters
        ----------
        uuid : str
            The ID of the object that should be deleted.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If parameter has the wrong type.
        ValueError
            If uuid is not properly formed.
        """

        if not isinstance(uuid, str):
            raise TypeError("UUID must be type str")
        if not validators.uuid(uuid):
            raise ValueError("UUID does not have proper form")

        try:
            response = self._connection.run_rest("/objects/" + uuid, REST_METHOD_DELETE)
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, object could not be deleted.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 204:
            # Successfully deleted
            return
        raise UnexpectedStatusCodeException("Delete object", response)

    def exists(self, uuid: str) -> bool:
        """
        Check if the object exist in weaviate.

        Parameters
        ----------
        uuid : str
            The UUID of the object that may or may not exist within weaviate.

        Returns
        -------
        bool
            True if object exists, False otherwise.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If parameter has the wrong type.
        ValueError
            If uuid is not properly formed.
        """

        response = self._get_object_response(uuid, None, False)

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        raise UnexpectedStatusCodeException("Object exists", response)

    def validate(self,
            data_object: Union[dict, str],
            class_name: str,
            uuid: str
        ) -> dict:
        """
        Validate an object against weaviate.

        Parameters
        ----------
        data_object : dict or str
            Object to be validated.
            If type is str it should be either an URL or a file.
        class_name : str
            Name of the class of the object that should be validated.
        uuid : str
            The UUID of the object that shoudl be validated against weaviate.

        Returns
        -------
        dict
            Validation result. E.g.
            {
                "valid": bool,
                "error": None or list
            }

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        weaviate.UnexpectedStatusCodeException
            If validating the object against weavate failed with a different reason.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        """

        if not isinstance(uuid, str):
            raise TypeError("UUID must be of type str")

        loaded_data_object = _get_dict_from_object(data_object)
        if not isinstance(class_name, str):
            raise TypeError(f"Expected class_name of type str but was: {type(class_name)}")

        weaviate_obj = {
            "id": uuid,
            "class": class_name,
            "properties": loaded_data_object
        }

        path = "/objects/validate"
        try:
            response = self._connection.run_rest(path, REST_METHOD_POST, weaviate_obj)
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, object was not validated against weaviate.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])

        result: dict = {
            "error": None
        }

        if response.status_code == 200:
            result["valid"] = True
            return result
        if response.status_code == 422:
            result["valid"] = False
            result["error"] = response.json()["error"]
            return result
        raise UnexpectedStatusCodeException("Validate object", response)


def _get_params(additional_properties: Optional[List[str]], with_vector: bool) -> dict:
    """
    Get underscor properties in the format accepted by weaviate.

    Parameters
    ----------
    additional_properties : list of str or None
        A list of additional properties or None.
    with_vector: bool
        If True the `vector` property will be returned too.

    Returns
    -------
    dict
        A dictionary including weaviate-accepted additional properties
        and/or `vector` property.

    Raises
    ------
    TypeError
        If 'additional_properties' is not of type list.
    """

    params = {}
    if additional_properties is not None:
        if not isinstance(additional_properties, list):
            raise TypeError(f"Additional properties must be of type list \
                                but are {type(additional_properties)}")
        params['include'] = ",".join(additional_properties)

    if with_vector:
        if 'include' in params:
            params['include'] = params['include'] + ',vector'
        else:
            params['include'] = 'vector'
    return params
