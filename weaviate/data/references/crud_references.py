"""
Reference class definition.
"""
from typing import Union, Optional
from weaviate.connect import Connection
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.util import (
    get_valid_uuid,
    deprecation,
    _capitalize_first_letter,
)


class Reference:
    """
    Reference class used to manipulate references within objects.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Reference class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection

    def delete(self,
            from_uuid: str,
            from_property_name: str,
            to_uuid: str,
            from_class_name: Optional[str]=None,
        ) -> None:
        """
        Remove a reference to another object. Equal to removing one
        direction of an edge from the graph.

        Parameters
        ----------
        from_uuid : str
            The ID of the object that references another object.
        from_property_name : str
            The property from which the reference should be deleted.
        to_uuid : str
            The UUID of the referenced object.
        from_class_name : Optional[str], optional
            The class name of the object for which to delete the reference, this is included in
            Weaviate v1.14.0, where all objects are namespaced by class name. If None it uses the
            old APIs, this will be required in the future releases. By default None.

        Examples
        --------
        Assume we have two classes, Author and Book.

        >>> # Create the objects first
        >>> client.data_object.create(
        ...     data_object = {'name': 'Ray Bradbury'},
        ...     class_name = 'Author',
        ...     uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab'
        ... )
        >>> client.data_object.create(
        ...     data_object = {'title': 'The Martian Chronicles'},
        ...     class_name = 'Book',
        ...     uuid = 'a9c1b714-4f8a-4b01-a930-38b046d69d2d'
        ... )
        >>> # Add the cross references
        >>> ## Author -> Book
        >>> client.data_object.reference.add(
        ...     from_uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab', # Author UUID
        ...     from_property_name = 'wroteBooks',
        ...     to_uuid = 'a9c1b714-4f8a-4b01-a930-38b046d69d2d' # Book UUID
        ... )
        >>> client.data_object.get('e067f671-1202-42c6-848b-ff4d1eb804ab') # Author UUID
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617177700595,
            "id": "e067f671-1202-42c6-848b-ff4d1eb804ab",
            "lastUpdateTimeUnix": 1617177700595,
            "properties": {
                "name": "Ray Bradbury",
                "wroteBooks": [
                {
                    "beacon": "weaviate://localhost/a9c1b714-4f8a-4b01-a930-38b046d69d2d",
                    "href": "/v1/objects/a9c1b714-4f8a-4b01-a930-38b046d69d2d"
                }
                ]
            },
            "vectorWeights": null
        }
        >>> # delete the reference
        >>> client.data_object.reference.delete(
        ...     from_uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab', # Author UUID
        ...     from_property_name = 'wroteBooks',
        ...     to_uuid = 'a9c1b714-4f8a-4b01-a930-38b046d69d2d' # Book UUID
        ... )
        >>> >>> client.data_object.get('e067f671-1202-42c6-848b-ff4d1eb804ab') # Author UUID
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617177700595,
            "id": "e067f671-1202-42c6-848b-ff4d1eb804ab",
            "lastUpdateTimeUnix": 1617177864970,
            "properties": {
                "name": "Ray Bradbury",
                "wroteBooks": []
            },
            "vectorWeights": null
        }

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

        # Validate arguments
        is_server_version_14 = (self._connection.server_version >= '1.14')

        if from_class_name is None and is_server_version_14:
            deprecation(
                "Weaviate Server version >= 1.14.x is using class namespaced APIs, please specify "
                "the `from_class_name` argument for this. The non-class namespaced APIs (None "
                "value for `from_class_name`) are going to be deprecated in the future versions "
                "of the Weaviate Server and Weaviate Python Client."
            )
        if from_class_name is not None:
            if not is_server_version_14:
                deprecation(
                    "Weaviate Server version < 1.14.x does not support class namespaced APIs. The "
                    "non-class namespaced APIs calls are going to be made instead (None value for "
                    "`class_name`). The non-class namespaced APIs are going to be deprecated "
                    "in the future versions of the Weaviate Server and Weaviate Python Client. "
                    "Please upgrade your Weaviate Server version."
                )
            if not isinstance(from_class_name, str):
                raise TypeError(
                    f"'class_name' must be of type str. Given type: {type(from_class_name)}"
                )
        from_uuid = get_valid_uuid(from_uuid)
        to_uuid = get_valid_uuid(to_uuid)
        _validate_property_name(from_property_name)

        # Create the beacon
        beacon = _get_beacon(to_uuid)

        if from_class_name and is_server_version_14:
            _class_name = _capitalize_first_letter(from_class_name)
            path = f"/objects/{_class_name}/{from_uuid}/references/{from_property_name}"
        else:
            path = f"/objects/{from_uuid}/references/{from_property_name}"

        try:
            response = self._connection.delete(
                path=path,
                weaviate_object=beacon
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Reference was not deleted.') from conn_err
        if response.status_code == 204:
            return
        raise UnexpectedStatusCodeException("Delete property reference to object", response)

    def update(self,
            from_uuid: str,
            from_property_name: str,
            to_uuids: Union[list, str],
            from_class_name: Optional[str]=None,
        ) -> None:
        """
        Allows to update all references in that property with a new set of references.
        All old references will be deleted.

        Parameters
        ----------
        from_uuid : str
            The object that should have the reference as part of its properties.
            Should be in the form of an UUID or in form of an URL.
            E.g.
            'http://localhost:8080/v1/objects/fc7eb129-f138-457f-b727-1b29db191a67'
            or
            'fc7eb129-f138-457f-b727-1b29db191a67'
        from_property_name : str
            The name of the property within the object.
        to_uuids : list or str
            The UUIDs of the objects that should be referenced.
            Should be a list of str in the form of an UUID or str in form of an URL.
            E.g.
            ['http://localhost:8080/v1/objects/fc7eb129-f138-457f-b727-1b29db191a67', ...]
            or
            ['fc7eb129-f138-457f-b727-1b29db191a67', ...]
            If `str` it is converted internally into a list of str.
        from_class_name : Optional[str], optional
            The class name of the object for which to update the reference, this is included in
            Weaviate v1.14.0, where all objects are namespaced by class name. If None it uses the
            old APIs, this will be required in the future releases. By default None.

        Examples
        --------
        You have data object 1 with reference property `wroteBooks` and currently has one reference
        to data object 7. Now you say, I want to update the references of data object 1.wroteBooks
        to this list 3,4,9. After the update, the data object 1.wroteBooks is now 3,4,9, but no
        longer contains 7.

        >>> client.data_object.get('e067f671-1202-42c6-848b-ff4d1eb804ab') # Author UUID
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617177700595,
            "id": "e067f671-1202-42c6-848b-ff4d1eb804ab",
            "lastUpdateTimeUnix": 1617177700595,
            "properties": {
                "name": "Ray Bradbury",
                "wroteBooks": [
                {
                    "beacon": "weaviate://localhost/a9c1b714-4f8a-4b01-a930-38b046d69d2d",
                    "href": "/v1/objects/a9c1b714-4f8a-4b01-a930-38b046d69d2d"
                }
                ]
            },
            "vectorWeights": null
        }
        Currently there is only one `Book` reference.
        Update all the references of the Author for property name `wroteBooks`.
        >>> client.data_object.reference.update(
        ...     from_uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab', # Author UUID
        ...     from_property_name = 'wroteBooks',
        ...     to_uuids = [
        ...         '8429f68f-860a-49ea-a50b-1f8789515882',
        ...         '3e2e6795-298b-47e9-a2cb-3d8a77a24d8a'
        ...     ]
        ... )
        >>> client.data_object.get('e067f671-1202-42c6-848b-ff4d1eb804ab') # Author UUID
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617181292677,
            "id": "e067f671-1202-42c6-848b-ff4d1eb804ab",
            "lastUpdateTimeUnix": 1617181409405,
            "properties": {
                "name": "Ray Bradbury",
                "wroteBooks": [
                {
                    "beacon": "weaviate://localhost/8429f68f-860a-49ea-a50b-1f8789515882",
                    "href": "/v1/objects/8429f68f-860a-49ea-a50b-1f8789515882"
                },
                {
                    "beacon": "weaviate://localhost/3e2e6795-298b-47e9-a2cb-3d8a77a24d8a",
                    "href": "/v1/objects/3e2e6795-298b-47e9-a2cb-3d8a77a24d8a"
                }
                ]
            },
            "vectorWeights": null
        }
        All the previous references were removed and now we have only those specified in the
        `update` method.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If the parameters are of the wrong type.
        ValueError
            If the parameters are of the wrong value.
        """

        is_server_version_14 = (self._connection.server_version >= '1.14')

        if from_class_name is None and is_server_version_14:
            deprecation(
                "Weaviate Server version >= 1.14.x is using class namespaced APIs, please specify "
                "the `from_class_name` argument for this. The non-class namespaced APIs (None "
                "value for `from_class_name`) are going to be deprecated in the future versions "
                "of the Weaviate Server and Weaviate Python Client."
            )
        if from_class_name is not None:
            if not is_server_version_14:
                deprecation(
                    "Weaviate Server version < 1.14.x does not support class namespaced APIs. The "
                    "non-class namespaced APIs calls are going to be made instead (None value for "
                    "`class_name`). The non-class namespaced APIs are going to be deprecated "
                    "in the future versions of the Weaviate Server and Weaviate Python Client. "
                    "Please upgrade your Weaviate Server version."
                )
            if not isinstance(from_class_name, str):
                raise TypeError(
                    f"'class_name' must be of type str. Given type: {type(from_class_name)}"
                )

        if not isinstance(to_uuids, list):
            to_uuids = [to_uuids]

        # Validate and create Beacon
        from_uuid = get_valid_uuid(from_uuid)
        _validate_property_name(from_property_name)
        beacons = []
        for to_uuid in to_uuids:
            to_uuid = get_valid_uuid(to_uuid)
            beacons.append(_get_beacon(to_uuid))

        if from_class_name and is_server_version_14:
            _class_name = _capitalize_first_letter(from_class_name)
            path = f"/objects/{_class_name}/{from_uuid}/references/{from_property_name}"
        else:
            path = f"/objects/{from_uuid}/references/{from_property_name}"

        try:
            response = self._connection.put(
                path=path,
                weaviate_object=beacons
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Reference was not updated.') from conn_err
        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeException("Update property reference to object", response)

    def add(self,
            from_uuid: str,
            from_property_name: str,
            to_uuid: str,
            from_class_name: Optional[str]=None,
        ) -> None:
        """
        Allows to link an object to an object uni-directionally.

        Parameters
        ----------
        from_uuid : str
            The ID of the object that should have the reference as part
            of its properties. Should be a plane UUID or an URL.
            E.g.
            'http://localhost:8080/v1/objects/fc7eb129-f138-457f-b727-1b29db191a67'
            or
            'fc7eb129-f138-457f-b727-1b29db191a67'
        from_property_name : str
            The name of the property within the object.
        to_uuid : str
            The UUID of the object that should be referenced.
            Should be a plane UUID or an URL.
            E.g.
            'http://localhost:8080/v1/objects/fc7eb129-f138-457f-b727-1b29db191a67'
            or
            'fc7eb129-f138-457f-b727-1b29db191a67'
        from_class_name : Optional[str], optional
            The class name of the object for which to add the reference, this is included in
            Weaviate v1.14.0, where all objects are namespaced by class name. If None it uses the
            old APIs, this will be required in the future releases. By default None.

        Examples
        --------
        Assume we have two classes, Author and Book.

        >>> # Create the objects first
        >>> client.data_object.create(
        ...     data_object = {'name': 'Ray Bradbury'},
        ...     class_name = 'Author',
        ...     uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab'
        ... )
        >>> client.data_object.create(
        ...     data_object = {'title': 'The Martian Chronicles'},
        ...     class_name = 'Book',
        ...     uuid = 'a9c1b714-4f8a-4b01-a930-38b046d69d2d'
        ... )
        >>> # Add the cross references
        >>> ## Author -> Book
        >>> client.data_object.reference.add(
        ...     from_uuid = 'e067f671-1202-42c6-848b-ff4d1eb804ab', # Author UUID
        ...     from_property_name = 'wroteBooks',
        ...     to_uuid = 'a9c1b714-4f8a-4b01-a930-38b046d69d2d' # Book UUID
        ... )
        >>> client.data_object.get('e067f671-1202-42c6-848b-ff4d1eb804ab') # Author UUID
        {
            "additional": {},
            "class": "Author",
            "creationTimeUnix": 1617177700595,
            "id": "e067f671-1202-42c6-848b-ff4d1eb804ab",
            "lastUpdateTimeUnix": 1617177700595,
            "properties": {
                "name": "Ray Bradbury",
                "wroteBooks": [
                {
                    "beacon": "weaviate://localhost/a9c1b714-4f8a-4b01-a930-38b046d69d2d",
                    "href": "/v1/objects/a9c1b714-4f8a-4b01-a930-38b046d69d2d"
                }
                ]
            },
            "vectorWeights": null
        }

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If the parameters are of the wrong type.
        ValueError
            If the parameters are of the wrong value.
        """

        is_server_version_14 = (self._connection.server_version >= '1.14')

        if from_class_name is None and is_server_version_14:
            deprecation(
                "Weaviate Server version >= 1.14.x is using class namespaced APIs, please specify "
                "the `from_class_name` argument for this. The non-class namespaced APIs (None "
                "value for `from_class_name`) are going to be deprecated in the future versions "
                "of the Weaviate Server and Weaviate Python Client."
            )
        if from_class_name is not None:
            if not is_server_version_14:
                deprecation(
                    "Weaviate Server version < 1.14.x does not support class namespaced APIs. The "
                    "non-class namespaced APIs calls are going to be made instead (None value for "
                    "`class_name`). The non-class namespaced APIs are going to be deprecated "
                    "in the future versions of the Weaviate Server and Weaviate Python Client. "
                    "Please upgrade your Weaviate Server version."
                )
            if not isinstance(from_class_name, str):
                raise TypeError(
                    f"'class_name' must be of type str. Given type: {type(from_class_name)}"
                )

        # Validate and create Beacon
        from_uuid = get_valid_uuid(from_uuid)
        to_uuid = get_valid_uuid(to_uuid)
        _validate_property_name(from_property_name)
        beacons = _get_beacon(to_uuid)

        if from_class_name and is_server_version_14:
            _class_name = _capitalize_first_letter(from_class_name)
            path = f"/objects/{_class_name}/{from_uuid}/references/{from_property_name}"
        else:
            path = f"/objects/{from_uuid}/references/{from_property_name}"

        try:
            response = self._connection.post(
                path=path,
                weaviate_object=beacons
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Reference was not added.') from conn_err
        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeException("Add property reference to object", response)


def _get_beacon(to_uuid: str) -> dict:
    """
    Get a weaviate-style beacon.

    Parameters
    ----------
    to_uuid : str
        The UUID to create beacon for.

    Returns
    -------
    dict
        Weaviate-style beacon as a dict.
    """

    return {
        "beacon": f"weaviate://localhost/{to_uuid}" # TODO: fix it
    }


def _validate_property_name(property_name: str) -> None:
    """
    Validate the property name.

    Parameters
    ----------
    property_name : str
        Property name to be validated.

    Raises
    ------
    TypeError
        If 'property_name' is not of type str.
    """

    if not isinstance(property_name, str):
        raise TypeError(
            f"'from_property_name' must be of type 'str'. Given type: {type(property_name)}"
        )
