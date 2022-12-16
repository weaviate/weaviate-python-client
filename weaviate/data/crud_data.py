"""
DataObject class definition.
"""
import uuid as uuid_lib
import warnings
from typing import Union, Optional, List, Sequence

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.data.references import Reference
from weaviate.error_msgs import DATA_DEPRECATION_NEW_V14_CLS_NS_W, DATA_DEPRECATION_OLD_V14_CLS_NS_W
from weaviate.exceptions import (
    ObjectAlreadyExistsException,
    UnexpectedStatusCodeException,
)
from weaviate.util import (
    _get_dict_from_object,
    get_vector,
    get_valid_uuid,
    _capitalize_first_letter,
    _check_positive_num,
)


class DataObject:
    """
    DataObject class used to manipulate object to/from weaviate.

    Attributes
    ----------
    reference : weaviate.data.references.Reference
        A Reference object to create objects cross-references.
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

    def create(
        self,
        data_object: Union[dict, str],
        class_name: str,
        uuid: Union[str, uuid_lib.UUID, None] = None,
        vector: Optional[Sequence] = None,
    ) -> str:
        """
        Takes a dict describing the object and adds it to weaviate.

        Parameters
        ----------
        data_object : dict or str
            Object to be added.
            If type is str it should be either a URL or a file.
        class_name : str
            Class name associated with the object given.
        uuid : str, uuid.UUID or None, optional
            Object will be created under this uuid if it is provided.
            Otherwise, weaviate will generate a uuid for this object,
            by default None.
        vector: Sequence or None, optional
            The embedding of the object that should be created. Used only class objects that do not
            have a vectorization module. Supported types are `list`, 'numpy.ndarray`,
            `torch.Tensor` and `tf.Tensor`,
            by default None.

        Examples
        --------
        Schema contains a class Author with only 'name' and 'age' primitive property.

        >>> client.data_object.create(
        ...     data_object = {'name': 'Neil Gaiman', 'age': 60},
        ...     class_name = 'Author',
        ... )
        '46091506-e3a0-41a4-9597-10e3064d8e2d'
        >>> client.data_object.create(
        ...     data_object = {'name': 'Andrzej Sapkowski', 'age': 72},
        ...     class_name = 'Author',
        ...     uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab'
        ... )
        'e067f671-1202-42c6-848b-ff4d1eb804ab'

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
            If creating the object in Weaviate failed for a different reason,
            more information is given in the exception.
        requests.ConnectionError
            If the network connection to weaviate fails.
        """

        if not isinstance(class_name, str):
            raise TypeError(f"Expected class_name of type str but was: {type(class_name)}")
        loaded_data_object = _get_dict_from_object(data_object)

        weaviate_obj = {
            "class": _capitalize_first_letter(class_name),
            "properties": loaded_data_object,
        }
        if uuid is not None:
            weaviate_obj["id"] = get_valid_uuid(uuid)

        if vector is not None:
            weaviate_obj["vector"] = get_vector(vector)

        path = "/objects"
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not added to Weaviate.") from conn_err
        if response.status_code == 200:
            return str(response.json()["id"])

        object_does_already_exist = False
        try:
            if "already exists" in response.json()["error"][0]["message"]:
                object_does_already_exist = True
        except KeyError:
            pass
        if object_does_already_exist:
            raise ObjectAlreadyExistsException(str(uuid))
        raise UnexpectedStatusCodeException("Creating object", response)

    def update(
        self,
        data_object: Union[dict, str],
        class_name: str,
        uuid: Union[str, uuid_lib.UUID],
        vector: Optional[Sequence] = None,
    ) -> None:
        """
        Update the given object with the already existing object in weaviate.
        Overwrites only the specified fields, the unspecified ones remain unchanged.

        Parameters
        ----------
        data_object : dict or str
            The object states the fields that should be updated.
            Fields not specified by in the 'data_object' remain unchanged.
            Fields that are None will not be changed.
            If type is str it should be either an URL or a file.
        class_name : str
            The class name of the object.
        uuid : str or uuid.UUID
            The ID of the object that should be changed.
        vector: Sequence or None, optional
            The embedding of the object that should be updated. Used only class objects that do not
            have a vectorization module. Supported types are `list`, 'numpy.ndarray`,
            `torch.Tensor` and `tf.Tensor`,
            by default None.

        Examples
        --------
        >>> author_id = client.data_object.create(
        ...     data_object = {'name': 'Philip Pullman', 'age': 64},
        ...     class_name = 'Author'
        ... )
        >>> client.data_object.get(author_id)
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617111215172,
            "id": "bec2bca7-264f-452a-a5bb-427eb4add068",
            "lastUpdateTimeUnix": 1617111215172,
            "properties": {
                "age": 64,
                "name": "Philip Pullman"
            },
            "vectorWeights": null
        }
        >>> client.data_object.update(
        ...     data_object = {'age': 74},
        ...     class_name = 'Author',
        ...     uuid = author_id
        ... )
        >>> client.data_object.get(author_id)
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617111215172,
            "id": "bec2bca7-264f-452a-a5bb-427eb4add068",
            "lastUpdateTimeUnix": 1617111215172,
            "properties": {
                "age": 74,
                "name": "Philip Pullman"
            },
            "vectorWeights": null
        }

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none successful status.
        """
        weaviate_obj, path = self._create_object_for_update(data_object, class_name, uuid, vector)
        try:
            response = self._connection.patch(path=path, weaviate_object=weaviate_obj)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not updated.") from conn_err
        if response.status_code == 204:
            # Successful merge
            return
        raise UnexpectedStatusCodeException("Update of the object not successful", response)

    def replace(
        self,
        data_object: Union[dict, str],
        class_name: str,
        uuid: Union[str, uuid_lib.UUID],
        vector: Optional[Sequence] = None,
    ) -> None:
        """
        Replace an already existing object with the given data object.
        This method replaces the whole object.

        Parameters
        ----------
        data_object : dict or str
            Describes the new values. It may be an URL or path to a json
            or a python dict describing the new values.
        class_name : str
            Name of the class of the object that should be updated.
        uuid : str or uuid.UUID
            The UUID of the object that should be changed.
        vector: Sequence or None, optional
            The embedding of the object that should be replaced. Used only class objects that do not
            have a vectorization module. Supported types are `list`, 'numpy.ndarray`,
            `torch.Tensor` and `tf.Tensor`,
            by default None.

        Examples
        --------
        >>> author_id = client.data_object.create(
        ...     data_object = {'name': 'H. Lovecraft', 'age': 46},
        ...     class_name = 'Author'
        ... )
        >>> client.data_object.get(author_id)
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617112817487,
            "id": "d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
            "lastUpdateTimeUnix": 1617112817487,
            "properties": {
                "age": 46,
                "name": "H. Lovecraft"
            },
            "vectorWeights": null
        }
        >>> client.data_object.replace(
        ...     data_object = {'name': 'H.P. Lovecraft'},
        ...     class_name = 'Author',
        ...     uuid = author_id
        ... )
        >>> client.data_object.get(author_id)
        {
            "additional": {},
            "class": "Author",
            "id": "d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
            "lastUpdateTimeUnix": 1617112838668,
            "properties": {
                "name": "H.P. Lovecraft"
            },
            "vectorWeights": null
        }

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """
        weaviate_obj, path = self._create_object_for_update(data_object, class_name, uuid, vector)
        try:
            response = self._connection.put(path=path, weaviate_object=weaviate_obj)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not replaced.") from conn_err
        if response.status_code == 200:
            # Successful update
            return
        raise UnexpectedStatusCodeException("Replace object", response)

    def _create_object_for_update(
        self,
        data_object: Union[dict, str],
        class_name: str,
        uuid: Union[str, uuid_lib.UUID],
        vector: Optional[Sequence] = None,
    ):
        if not isinstance(class_name, str):
            raise TypeError("Class must be type str")

        uuid = get_valid_uuid(uuid)

        object_dict = _get_dict_from_object(data_object)

        weaviate_obj = {
            "id": uuid,
            "properties": object_dict,
            "class": _capitalize_first_letter(class_name),
        }

        if vector is not None:
            weaviate_obj["vector"] = get_vector(vector)

        is_server_version_14 = self._connection.server_version >= "1.14"

        if is_server_version_14:
            path = f"/objects/{_capitalize_first_letter(class_name)}/{uuid}"
        else:
            path = f"/objects/{uuid}"
        return weaviate_obj, path

    def get_by_id(
        self,
        uuid: Union[str, uuid_lib.UUID],
        additional_properties: List[str] = None,
        with_vector: bool = False,
        class_name: Optional[str] = None,
        node_name: Optional[str] = None,
        consistency_level: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get an object as dict.

        Parameters
        ----------
        uuid : str or uuid.UUID
            The identifier of the object that should be retrieved.
        additional_properties : list of str, optional
            List of additional properties that should be included in the request,
            by default None
        with_vector: bool
            If True the `vector` property will be returned too,
            by default False.
        class_name : Optional[str], optional
            The class name of the object with UUID `uuid`. Introduced in Weaviate version v1.14.0.
            STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
            versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < v1.14.0,
            by default None

        Examples
        --------
        >>> client.data_object.get_by_id(
        ...     uuid="d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
        ...     class_name='Author', # ONLY with Weaviate >= 1.14.0
        ... )
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617112817487,
            "id": "d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
            "lastUpdateTimeUnix": 1617112817487,
            "properties": {
                "age": 46,
                "name": "H.P. Lovecraft"
            },
            "vectorWeights": null
        }

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
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        return self.get(
            uuid=uuid,
            additional_properties=additional_properties,
            with_vector=with_vector,
            class_name=class_name,
            node_name=node_name,
            consistency_level=consistency_level
        )

    def get(
        self,
        uuid: Union[str, uuid_lib.UUID, None] = None,
        additional_properties: List[str] = None,
        with_vector: bool = False,
        class_name: Optional[str] = None,
        limit: Optional[int] = None,
        node_name: Optional[str] = None,
        consistency_level: Optional[str] = None
    ) -> List[dict]:
        """
        Gets objects from weaviate, the maximum number of objects returned is 100.
        If 'uuid' is None, all objects are returned. If 'uuid' is specified the result is the same
        as for `get_by_uuid` method.

        Parameters
        ----------
        uuid : str, uuid.UUID or None, optional
            The identifier of the object that should be retrieved.
        additional_properties : list of str, optional
            list of additional properties that should be included in the request,
            by default None
        with_vector : bool
            If True the `vector` property will be returned too,
            by default False
        class_name: Optional[str], optional
            The class name of the object with UUID `uuid`. Introduced in Weaviate version v1.14.0.
            STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
            versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < v1.14.0,
            by default None
        limit: Optional[int], optional
            The maximum number of data objects to return.
            by default None, which uses the weaviate default of 100 entries
        consistency_level : Optional[str], optional
            Can be one of 'ALL', 'ONE', or 'QUORUM'. Determines how many replicas must acknowledge
            a request before it is considered successful. Mutually exclusive with node_name param.
        node_name : Optional[str], optional
            The name of the target node which should fulfill the request. Mutually exclusive with
            consistency_level param.

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
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """
        is_server_version_14 = self._connection.server_version >= "1.14"

        if class_name is None and is_server_version_14 and uuid is not None:
            warnings.warn(
                message=DATA_DEPRECATION_NEW_V14_CLS_NS_W,
                category=DeprecationWarning,
                stacklevel=1,
            )
        if class_name is not None and uuid is not None:
            if not is_server_version_14:
                warnings.warn(
                    message=DATA_DEPRECATION_OLD_V14_CLS_NS_W,
                    category=DeprecationWarning,
                    stacklevel=1,
                )
            if not isinstance(class_name, str):
                raise TypeError(f"'class_name' must be of type str. Given type: {type(class_name)}")

        params = _get_params(additional_properties, with_vector)

        if class_name and is_server_version_14:
            if uuid is not None:
                path = f"/objects/{_capitalize_first_letter(class_name)}"
            else:
                path = "/objects"
                params["class"] = _capitalize_first_letter(class_name)
        else:
            path = "/objects"

        if uuid is not None:
            path += "/" + get_valid_uuid(uuid)

        if limit is not None:
            _check_positive_num(limit, "limit", int)
            params["limit"] = limit

        if consistency_level is not None:
            params["consistency_level"] = consistency_level

        if node_name is not None:
            params["node_name"] = node_name

        try:
            response = self._connection.get(
                path=path,
                params=params,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not get object/s.") from conn_err
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Get object/s", response)

    def delete(
        self,
        uuid: Union[str, uuid_lib.UUID],
        class_name: Optional[str] = None,
    ) -> None:
        """
        Delete an existing object from weaviate.

        Parameters
        ----------
        uuid : str or uuid.UUID
            The ID of the object that should be deleted.
        class_name : Optional[str], optional
            The class name of the object with UUID `uuid`. Introduced in Weaviate version v1.14.0.
            STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
            versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < v1.14.0,
            by default None

        Examples
        --------
        >>> client.data_object.get(
        ...     uuid="d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
        ...     class_name='Author', # ONLY with Weaviate >= 1.14.0
        ... )
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617112817487,
            "id": "d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
            "lastUpdateTimeUnix": 1617112817487,
            "properties": {
                "age": 46,
                "name": "H.P. Lovecraft"
            },
            "vectorWeights": null
        }
        >>> client.data_object.delete(
        ...     uuid="d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
        ...     class_name='Author', # ONLY with Weaviate >= 1.14.0
        ... )
        >>> client.data_object.get(
        ...     uuid="d842a0f4-ad8c-40eb-80b4-bfefc7b1b530",
        ...     class_name='Author', # ONLY with Weaviate >= 1.14.0
        ... )
        None

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If parameter has the wrong type.
        ValueError
            If uuid is not properly formed.
        """

        uuid = get_valid_uuid(uuid)

        is_server_version_14 = self._connection.server_version >= "1.14"

        if class_name is None and is_server_version_14:
            warnings.warn(
                message=DATA_DEPRECATION_NEW_V14_CLS_NS_W,
                category=DeprecationWarning,
                stacklevel=1,
            )
        if class_name is not None:
            if not is_server_version_14:
                warnings.warn(
                    message=DATA_DEPRECATION_OLD_V14_CLS_NS_W,
                    category=DeprecationWarning,
                    stacklevel=1,
                )
            if not isinstance(class_name, str):
                raise TypeError(f"'class_name' must be of type str. Given type: {type(class_name)}")

        if class_name and is_server_version_14:
            path = f"/objects/{_capitalize_first_letter(class_name)}/{uuid}"
        else:
            path = f"/objects/{uuid}"

        try:
            response = self._connection.delete(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object could not be deleted.") from conn_err
        if response.status_code == 204:
            # Successfully deleted
            return
        raise UnexpectedStatusCodeException("Delete object", response)

    def exists(
        self,
        uuid: Union[str, uuid_lib.UUID],
        class_name: Optional[str] = None,
    ) -> bool:
        """
        Check if the object exist in weaviate.

        Parameters
        ----------
        uuid : str or uuid.UUID
            The UUID of the object that may or may not exist within Weaviate.
        class_name : Optional[str], optional
            The class name of the object with UUID `uuid`. Introduced in Weaviate version 1.14.0.
            STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
            versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < 1.14.0,
            by default None

        Examples
        --------
        >>> client.data_object.exists(
        ...     uuid='e067f671-1202-42c6-848b-ff4d1eb804ab',
        ...     class_name='Author',  # ONLY with Weaviate >= 1.14.0
        ... )
        False
        >>> client.data_object.create(
        ...     data_object = {'name': 'Andrzej Sapkowski', 'age': 72},
        ...     class_name = 'Author',
        ...     uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab'
        ... )
        >>> client.data_object.exists(
        ...     uuid='e067f671-1202-42c6-848b-ff4d1eb804ab',
        ...     class_name='Author', # ONLY with Weaviate >= 1.14.0
        ... )
        True

        Returns
        -------
        bool
            True if object exists, False otherwise.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If parameter has the wrong type.
        ValueError
            If uuid is not properly formed.
        """

        is_server_version_14 = self._connection.server_version >= "1.14"

        if class_name is None and is_server_version_14:
            warnings.warn(
                message=DATA_DEPRECATION_NEW_V14_CLS_NS_W,
                category=DeprecationWarning,
                stacklevel=1,
            )
        if class_name is not None:
            if not is_server_version_14:
                warnings.warn(
                    message=DATA_DEPRECATION_OLD_V14_CLS_NS_W,
                    category=DeprecationWarning,
                    stacklevel=1,
                )
            if not isinstance(class_name, str):
                raise TypeError(f"'class_name' must be of type str. Given type: {type(class_name)}")

        if class_name and is_server_version_14:
            path = f"/objects/{_capitalize_first_letter(class_name)}/{get_valid_uuid(uuid)}"
        else:
            path = f"/objects/{get_valid_uuid(uuid)}"

        try:
            response = self._connection.head(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not check if object exist.") from conn_err

        if response.status_code == 204:
            return True
        if response.status_code == 404:
            return False
        raise UnexpectedStatusCodeException("Object exists", response)

    def validate(
        self,
        data_object: Union[dict, str],
        class_name: str,
        uuid: Union[str, uuid_lib.UUID, None] = None,
        vector: Sequence = None,
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
        uuid : str, uuid.UUID or None, optional
            The UUID of the object that should be validated against weaviate.
            by default None.
        vector: Sequence, optional
            The embedding of the object that should be validated. Used only class objects that
            do not have a vectorization module. Supported types are `list`, 'numpy.ndarray`,
            `torch.Tensor` and `tf.Tensor`,
            by default None.

        Examples
        --------
        Assume we have a Author class only 'name' property, NO 'age'.

        >>> client1.data_object.validate(
        ...     data_object = {'name': 'H. Lovecraft'},
        ...     class_name = 'Author'
        ... )
        {'error': None, 'valid': True}
        >>> client1.data_object.validate(
        ...     data_object = {'name': 'H. Lovecraft', 'age': 46},
        ...     class_name = 'Author'
        ... )
        {
            "error": [
                {
                "message": "invalid object: no such prop with name 'age' found in class 'Author'
                    in the schema. Check your schema files for which properties in this class are
                    available"
                }
            ],
            "valid": false
        }

        Returns
        -------
        dict
            Validation result. E.g. {"valid": bool, "error": None or list}

        Raises
        ------
        TypeError
            If argument is of wrong type.
        ValueError
            If argument contains an invalid value.
        weaviate.UnexpectedStatusCodeException
            If validating the object against Weaviate failed with a different reason.
        requests.ConnectionError
            If the network connection to weaviate fails.
        """

        loaded_data_object = _get_dict_from_object(data_object)
        if not isinstance(class_name, str):
            raise TypeError(f"Expected class_name of type `str` but was: {type(class_name)}")

        weaviate_obj = {
            "class": _capitalize_first_letter(class_name),
            "properties": loaded_data_object,
        }

        if uuid is not None:
            weaviate_obj["id"] = get_valid_uuid(uuid)

        if vector is not None:
            weaviate_obj["vector"] = get_vector(vector)

        path = "/objects/validate"
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Object was not validated against weaviate."
            ) from conn_err

        result: dict = {"error": None}

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
    Get underscore properties in the format accepted by weaviate.

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
    if additional_properties:
        if not isinstance(additional_properties, list):
            raise TypeError(
                "Additional properties must be of type list "
                f"but are {type(additional_properties)}"
            )
        params["include"] = ",".join(additional_properties)

    if with_vector:
        if "include" in params:
            params["include"] = params["include"] + ",vector"
        else:
            params["include"] = "vector"
    return params
