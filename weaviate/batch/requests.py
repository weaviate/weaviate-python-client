from __future__ import unicode_literals
import copy
import validators
from weaviate.util import is_weaviate_entity_url, get_uuid_from_weaviate_url


class ReferenceBatchRequest:
    """
    Collect references to add them in one request to weaviate.
    Caution this request will miss some validations to be faster.
    """

    def __init__(self):
        self._from_entity_class_names = []
        self._from_entity_ids = []
        self._from_entity_properties = []
        self._to_entity_ids = []

    def __len__(self):
        return len(self._from_entity_class_names)

    def get_batch_size(self) -> int:
        """
        Get current number of references that are not yet uploaded to weaviate.

        Returns
        -------
        int
            Number of references.
        """

        return len(self._from_entity_class_names)

    def add_reference(self,
            from_entity_uuid: str,
            from_entity_class_name: str,
            from_property_name: str,
            to_entity_uuid: str
        ) -> None:
        """
        Add one reference to this batch.

        Parameters
        ----------
        from_entity_uuid : str
            The UUID or URL of the thing that should reference another object.
        from_entity_class_name : str
            The name of the class that should reference another object.
        from_property_name : str
            The name of the property that contains the reference.
        to_entity_uuid : str
            The UUID or URL of the object that is actually referenced.

        Raises
        ------
        TypeError
            If arguments are not string.
        """

        if not isinstance(from_entity_class_name, str) or not isinstance(from_entity_uuid, str) or\
            not isinstance(from_property_name, str) or not isinstance(to_entity_uuid, str):
            raise TypeError('All arguments must be of type string')

        if is_weaviate_entity_url(from_entity_uuid):
            from_entity_uuid = get_uuid_from_weaviate_url(from_entity_uuid)
        if is_weaviate_entity_url(to_entity_uuid):
            to_entity_uuid = get_uuid_from_weaviate_url(to_entity_uuid)

        self._from_entity_class_names.append(from_entity_class_name)
        self._from_entity_ids.append(from_entity_uuid)
        self._from_entity_properties.append(from_property_name)
        self._to_entity_ids.append(to_entity_uuid)

    def get_request_body(self) -> list:
        """
        Get request body as a list of dictionaries, where each dictionary
        is a weaviate-schema reference.

        Returns
        -------
        list
            A list of references as dictionaries.
        """

        batch_body = [None] * self.get_batch_size()
        for i in range(self.get_batch_size()):
            batch_body[i] = {
                "from": "weaviate://localhost/" + self._from_entity_class_names[i] + "/"
                    + self._from_entity_ids[i] + "/" + self._from_entity_properties[i],
                "to": "weaviate://localhost/" + self._to_entity_ids[i]
            }
        return batch_body


class ObjectsBatchRequest:
    """
    Collect objects for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def __init__(self):
        self._objects = []

    def __len__(self):
        return len(self._objects)

    def add_object(self,
            data_object: dict,
            class_name: str,
            uuid: str = None
        ) -> None:
        """
        Add one object to this batch.

        Parameters
        ----------
        data_object : dict
            Object to be added as a dict datatype.
        class_name : str
            The name of the class this object belongs to.
        uuid : str, optional
            UUID of the object as a string, by default None

        Raises
        ------
        TypeError
            If 'data_object' is not of type dict.
        TypeError
            If 'class_name` is not of type str.
        TypeError
            If 'uuid' is not None and is not of type str.
        ValueError
            If 'uuid' is not of a propper form.
        """

        if not isinstance(data_object, dict):
            raise TypeError("Object must be of type dict")
        if not isinstance(class_name, str):
            raise TypeError("Class name must be of type str")

        batch_item = {
            "class": class_name,
            "schema": copy.deepcopy(data_object)
        }
        if uuid is not None:
            if not isinstance(uuid, str):
                raise TypeError("UUID must be of type str")
            if not validators.uuid(uuid):
                raise ValueError("UUID is not in a proper form")
            batch_item["id"] = uuid

        self._objects.append(batch_item)

    def get_request_body(self):
        """
        Get the request body as it is needed for weaviate

        Returns
        -------
        dict
            The request body as a dict.
        """
        return {
            "fields": [
                "ALL"
            ],
            "objects": self._objects
        }
