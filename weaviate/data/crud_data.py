"""
DataObject class definition.
"""

import uuid as uuid_lib
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, cast

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.data.references import Reference
from weaviate.data.replication import ConsistencyLevel
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
from weaviate.types import UUID


class DataObject:
    """
    DataObject class used to manipulate object to/from Weaviate.

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
            Connection object to an active and running Weaviate instance.
        """

        self._connection = connection
        self.reference = Reference(self._connection)

    def create(
        self,
        data_object: Union[dict, str],
        class_name: str,
        uuid: Union[str, uuid_lib.UUID, None] = None,
        vector: Optional[Sequence] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> str:
        """
        Takes a dict describing the object and adds it to Weaviate.

        Parameters
        ----------
        data_object : dict or str
            Object to be added.
            If type is str it should be either a URL or a file.
        class_name : str
            Class name associated with the object given.
        uuid : str, uuid.UUID or None, optional
            Object will be created under this uuid if it is provided.
            Otherwise, Weaviate will generate a uuid for this object,
            by default None.
        vector: Sequence or None, optional
            Embedding for the object.
            Can be used when:
             - a class does not have a vectorization module.
             - The given vector was generated using the _identical_ vectorization module that is configured for the
             class. In this case this vector takes precedence.

            Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`,
            by default None.
        consistency_level : Optional[ConsistencyLevel], optional
            Can be one of 'ALL', 'ONE', or 'QUORUM'. Determines how many replicas must acknowledge
        tenant: Optional[str], optional
            The name of the tenant for which this operation is being performed.

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
            If an object with the given uuid already exists within Weaviate.
        weaviate.UnexpectedStatusCodeException
            If creating the object in Weaviate failed for a different reason,
            more information is given in the exception.
        requests.ConnectionError
            If the network connection to Weaviate fails.
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
        params = {}
        if consistency_level is not None:
            params["consistency_level"] = ConsistencyLevel(consistency_level).value
        if tenant is not None:
            weaviate_obj["tenant"] = tenant
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj, params=params)
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
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """
        Update an already existing object in Weaviate with the given data object.
        Overwrites only the specified fields, the unspecified ones remain unchanged.

        Parameters
        ----------
        data_object : dict or str
            The object states the fields that should be updated.
            Fields not specified in the 'data_object' remain unchanged.
            Fields that are None will not be changed.
            If type is str it should be either an URL or a file.
        class_name : str
            The class name of the object.
        uuid : str or uuid.UUID
            The ID of the object that should be changed.
        vector: Sequence or None, optional
            Embedding for the object.
            Can be used when:
             - a class does not have a vectorization module.
             - The given vector was generated using the _identical_ vectorization module that is configured for the
             class. In this case this vector takes precedence.

            Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`,
            by default None.
        consistency_level : Optional[ConsistencyLevel], optional
            Can be one of 'ALL', 'ONE', or 'QUORUM'. Determines how many replicas must acknowledge
        tenant: Optional[str], optional
            The name of the tenant for which this operation is being performed.

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
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a none successful status.
        """
        params = {}
        if consistency_level is not None:
            params["consistency_level"] = ConsistencyLevel(consistency_level).value
        weaviate_obj, path = self._create_object_for_update(data_object, class_name, uuid, vector)
        if tenant is not None:
            weaviate_obj["tenant"] = tenant

        try:
            response = self._connection.patch(
                path=path,
                weaviate_object=weaviate_obj,
                params=params,
            )
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
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
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
            Embedding for the object.
            Can be used when:
             - a class does not have a vectorization module.
             - The given vector was generated using the _identical_ vectorization module that is configured for the
             class. In this case this vector takes precedence.

            Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`,
            by default None.
        consistency_level : Optional[ConsistencyLevel], optional
            Can be one of 'ALL', 'ONE', or 'QUORUM'. Determines how many replicas must acknowledge
        tenant: Optional[str], optional
            The name of the tenant for which this operation is being performed.

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
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a none OK status.
        """
        params = {}
        if consistency_level is not None:
            params["consistency_level"] = ConsistencyLevel(consistency_level).value
        weaviate_obj, path = self._create_object_for_update(data_object, class_name, uuid, vector)
        if tenant is not None:
            weaviate_obj["tenant"] = tenant
        try:
            response = self._connection.put(path=path, weaviate_object=weaviate_obj, params=params)
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
    ) -> Tuple[Dict[str, Any], str]:
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
        additional_properties: Optional[List[str]] = None,
        with_vector: bool = False,
        class_name: Optional[str] = None,
        node_name: Optional[str] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
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
        tenant: str, optional
            The name of the tenant for which this operation is being performed.

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
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a none OK status.
        """

        return self.get(
            uuid=uuid,
            additional_properties=additional_properties,
            with_vector=with_vector,
            class_name=class_name,
            node_name=node_name,
            consistency_level=consistency_level,
            tenant=tenant,
        )

    def get(
        self,
        uuid: Union[str, uuid_lib.UUID, None] = None,
        additional_properties: Optional[List[str]] = None,
        with_vector: bool = False,
        class_name: Optional[str] = None,
        node_name: Optional[str] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
        limit: Optional[int] = None,
        after: Optional[UUID] = None,
        offset: Optional[int] = None,
        sort: Optional[Dict[str, Union[str, bool, List[bool], List[str]]]] = None,
        tenant: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Gets objects from Weaviate, the maximum number of objects returned is 100.
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
        consistency_level : Optional[ConsistencyLevel], optional
            Can be one of 'ALL', 'ONE', or 'QUORUM'. Determines how many replicas must acknowledge
            a request before it is considered successful. Mutually exclusive with node_name param.
        node_name : Optional[str], optional
            The name of the target node which should fulfill the request. Mutually exclusive with
            consistency_level param.
        limit: Optional[int], optional
            The maximum number of data objects to return.
            by default None, which uses the Weaviate default of 100 entries
        after: Optional[UUID], optional
           Can be used to extract all elements by giving the last ID from the previous "page". Requires limit to be set
           but cannot be combined with any other filters or search. Part of the Cursor API.
        offset: Optional[int], optional
            The offset of objects returned, i.e. the starting index of the returned objects. Should be
            used in conjunction with the 'limit' parameter.
        sort: Optional[Dict]
            A dictionary for sorting objects.
            sort['properties']: str, List[str]
                By which properties the returned objects should be sorted. When more than one property is given, the objects are sorted in order of the list.
                The order of the sorting can be given by using 'sort['order_asc']'.
            sort['order_asc']: bool, List[bool]
                The order the properties given in 'sort['properties']' should be returned in. When a single boolean is used, all properties are sorted in the same order.
                If a list is used, it needs to have the same length as 'sort'. Each properties order is then decided individually.
                If 'sort['order_asc']' is True, the properties are sorted in ascending order. If it is False, they are sorted in descending order.
                if 'sort['order_asc']' is not given, all properties are sorted in ascending order.
        tenant: Optional[str], optional
            The name of the tenant for which this operation is being performed.

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
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a none OK status.
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

        if consistency_level is not None:
            params["consistency_level"] = ConsistencyLevel(consistency_level).value

        if tenant is not None:
            params["tenant"] = tenant

        if node_name is not None:
            params["node_name"] = node_name

        if limit is not None:
            _check_positive_num(limit, "limit", int, include_zero=False)
            params["limit"] = limit

        if after is not None:
            params["after"] = get_valid_uuid(after)

        if offset is not None:
            _check_positive_num(offset, "offset", int, include_zero=True)
            params["offset"] = offset

        if sort is not None:
            if "properties" not in sort:
                raise ValueError("The sort clause is missing the required field: 'properties'.")
            if "order_asc" not in sort:
                sort["order_asc"] = True
            if not isinstance(sort, Dict):
                raise TypeError(f"'sort' must be of type dict. Given type: {type(sort)}.")
            if isinstance(sort["properties"], str):
                sort["properties"] = [sort["properties"]]
            elif not isinstance(sort["properties"], list) or not all(
                isinstance(x, str) for x in sort["properties"]
            ):
                raise TypeError(
                    f"'sort['properties']' must be of type str or list[str]. Given type: {type(sort['properties'])}."
                )
            if len(sort["properties"]) == 0:
                raise ValueError("'sort['properties']' cannot be an empty list.")

            if isinstance(sort["order_asc"], bool):
                sort["order_asc"] = [sort["order_asc"]] * len(sort["properties"])
            elif not isinstance(sort["order_asc"], list) or not all(
                isinstance(x, bool) for x in sort["order_asc"]
            ):
                raise TypeError(
                    f"'sort['order_asc']' must be of type boolean or list[bool]. Given type: {type(sort['order_asc'])}."
                )
            if len(sort["properties"]) != len(sort["order_asc"]):  # type: ignore
                raise ValueError(
                    f"'sort['order_asc']' must be the same length as 'sort['properties']' or a boolean (not in a list). Current length is sort['properties']:{len(sort['properties'])} and sort['order_asc']:{len(sort['order_asc'])}."  # type: ignore
                )
            if len(sort["order_asc"]) == 0:  # type: ignore
                raise ValueError("'sort['order_asc']' cannot be an empty list.")

            params["sort"] = ",".join(sort["properties"])  # type: ignore
            order = ["asc" if x else "desc" for x in sort["order_asc"]]  # type: ignore
            params["order"] = ",".join(order)

        try:
            response = self._connection.get(
                path=path,
                params=params,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not get object/s.") from conn_err
        if response.status_code == 200:
            return cast(Dict[str, Any], response.json())
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Get object/s", response)

    def delete(
        self,
        uuid: Union[str, uuid_lib.UUID],
        class_name: Optional[str] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """
        Delete an existing object from Weaviate.

        Parameters
        ----------
        uuid : str or uuid.UUID
            The ID of the object that should be deleted.
        class_name : Optional[str], optional
            The class name of the object with UUID `uuid`. Introduced in Weaviate version v1.14.0.
            STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
            versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < v1.14.0,
            by default None
        consistency_level : Optional[ConsistencyLevel], optional
            Can be one of 'ALL', 'ONE', or 'QUORUM'. Determines how many replicas must acknowledge
        tenant: str, optional
            The name of the tenant for which this operation is being performed.

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
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a none OK status.
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

        params = {}
        if consistency_level is not None:
            params = {"consistency_level": ConsistencyLevel(consistency_level).value}
        if tenant is not None:
            params["tenant"] = tenant
        try:
            response = self._connection.delete(
                path=path,
                params=params,
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
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> bool:
        """
        Check if the object exist in Weaviate.

        Parameters
        ----------
        uuid : str or uuid.UUID
            The UUID of the object that may or may not exist within Weaviate.
        class_name : Optional[str], optional
            The class name of the object with UUID `uuid`. Introduced in Weaviate version 1.14.0.
            STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
            versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < 1.14.0,
            by default None
        consistency_level : Optional[ConsistencyLevel], optional
            Can be one of 'ALL', 'ONE', or 'QUORUM'. Determines how many replicas must acknowledge
        tenant: Optional[str], optional
            The name of the tenant for which this operation is being performed.

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
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a none OK status.
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
        params = {}
        if consistency_level is not None:
            params = {"consistency_level": ConsistencyLevel(consistency_level).value}
        if tenant is not None:
            params["tenant"] = tenant

        try:
            response = self._connection.head(
                path=path,
                params=params,
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
        vector: Optional[Sequence] = None,
    ) -> dict:
        """
        Validate an object against Weaviate.

        Parameters
        ----------
        data_object : dict or str
            Object to be validated.
            If type is str it should be either an URL or a file.
        class_name : str
            Name of the class of the object that should be validated.
        uuid : str, uuid.UUID or None, optional
            The UUID of the object that should be validated against Weaviate.
            by default None.
        vector: Sequence or None, optional
            The embedding of the object that should be validated.
            Can be used when:
             - a class does not have a vectorization module.
             - The given vector was generated using the _identical_ vectorization module that is configured for the
             class. In this case this vector takes precedence.

            Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`,
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
            If the network connection to Weaviate fails.
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
                "Object was not validated against Weaviate."
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
    Get underscore properties in the format accepted by Weaviate.

    Parameters
    ----------
    additional_properties : list of str or None
        A list of additional properties or None.
    with_vector: bool
        If True the `vector` property will be returned too.

    Returns
    -------
    dict
        A dictionary including Weaviate-accepted additional properties
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
