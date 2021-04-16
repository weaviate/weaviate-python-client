import sys
from typing import Union, List
from weaviate.connect import REST_METHOD_DELETE, REST_METHOD_PUT, REST_METHOD_POST, Connection
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.util import get_valid_uuid



class Reference:
    """
    Reference class used to manipulate refferences within objects.
    """

    # This is a class private variable that contains implemented
    # methods and their respective REST method and Success return code.
    _methods_to_rest = {
        "add" : {
            "rest" : REST_METHOD_POST,
            "success_code": 200,
        },
        "update" : {
            "rest" : REST_METHOD_PUT,
            "success_code" : 200,
        },
        "delete" : {
            "rest" : REST_METHOD_DELETE,
            "success_code" : 204
        }
    }

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
            to_uuid: str
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
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If parameter has the wrong type.
        ValueError
            If uuid is not properly formed.
        """

        self._try_run_rest(
            from_uuid=from_uuid,
            from_property_name=from_property_name,
            to_uuid_s=to_uuid,
            method="delete"
        )

    def update(self,
            from_uuid: str,
            from_property_name: str,
            to_uuids: Union[list, str]
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
            If `str` it is converted internaly into a list of str.

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
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If the parameters are of the wrong type.
        ValueError
            If the parameters are of the wrong value.
        """

        self._try_run_rest(
            from_uuid=from_uuid,
            from_property_name=from_property_name,
            to_uuid_s=to_uuids,
            method="update"
        )

    def add(self,
            from_uuid: str,
            from_property_name: str,
            to_uuid: str
        ) -> None:
        """
        Allows to link an object to an object unidirectionally.

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
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If the parameters are of the wrong type.
        ValueError
            If the parameters are of the wrong value.
        """

        self._try_run_rest(
            from_uuid=from_uuid,
            from_property_name=from_property_name,
            to_uuid_s=to_uuid,
            method="add"
        )

    def _try_run_rest(self,
            from_uuid: str,
            from_property_name: str,
            to_uuid_s: Union[str, List[str]],
            method: str
        ) -> None:
        """
        Try to run a rest method based on the 'method' argument.

        Parameters
        ----------
        from_uuid : str
            The ID of the object that should have the reference as part
            of its properties. Should be a plane UUID or an URL.
        from_property_name : str
            The name of the property within the object.
        to_uuid_s : Union[str, List[str]]
            The UUID/s of the object/s that should be referenced.
            It can be a string or a list of strings. List of string is only
            used for the 'update' method.
        method : str
            REST call method, check self._methods_to_rest to see what methods
            are available at the moment.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            If the parameters are of the wrong type.
        ValueError
            If the parameters are of the wrong value.
        """

        if method not in self._methods_to_rest.keys():
            raise ValueError(f"'{method}' not supported!")

        # Validate and create Beacon
        _from_uuid = get_valid_uuid(from_uuid)
        _validate_property_name(from_property_name)

        # Validate 'to_uuid_s' and create the respective beacon/s
        beacons = []
        if method == "update":
            # Update works with a list of 'to_uuids' so it needs a separate check.
            if not isinstance(to_uuid_s, list):
                to_uuid_s = [to_uuid_s]

            for to_uuid in to_uuid_s:
                _to_uuid = get_valid_uuid(to_uuid)
                beacons.append(_get_beacon(_to_uuid))
        else:
            # Other methods take just a UUID as a str
            _to_uuid = get_valid_uuid(to_uuid_s)
            beacons = _get_beacon(_to_uuid)

        # Try to Run REST method
        path = f"/objects/{_from_uuid}/references/{from_property_name}"
        try:
            response = self._connection.run_rest(
                path=path,
                rest_method=self._methods_to_rest[method]["rest"],
                weaviate_object=beacons
                )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + f' Connection error, did not {method} reference.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])

        if response.status_code == self._methods_to_rest[method]["success_code"]:
            return
        raise UnexpectedStatusCodeException(f"{method} property reference to object", response)


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
        "beacon": f"weaviate://localhost/{to_uuid}"
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
        raise TypeError("from_property_name must be of type 'str' but was: "\
                        + str(type(property_name)))
