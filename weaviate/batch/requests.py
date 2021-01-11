from __future__ import unicode_literals
import copy
import warnings
from abc import ABC, abstractmethod
from typing import List
import validators
from weaviate.util import is_weaviate_object_url, get_uuid_from_weaviate_url

class BatchRequest(ABC):
    """
    BatchRequest abstract class used as a interface for batch requests.
    """

    @abstractmethod
    def get_request_body(self):
        pass

class ReferenceBatchRequest(BatchRequest):
    """
    Collect references to add them in one request to weaviate.
    Caution this request will miss some validations to be faster.
    """

    def __init__(self):
        self._from_object_class_names = []
        self._from_object_ids = []
        self._from_object_properties = []
        self._to_object_ids = []

    def __len__(self):
        return len(self._from_object_class_names)

    def add(self,
            from_object_uuid: str,
            from_object_class_name: str,
            from_property_name: str,
            to_object_uuid: str
        ) -> None:
        """
        Add one reference to this batch.

        Parameters
        ----------
        from_object_uuid : str
            The UUID or URL of the object that should reference another object.
        from_object_class_name : str
            The name of the class that should reference another object.
        from_property_name : str
            The name of the property that contains the reference.
        to_object_uuid : str
            The UUID or URL of the object that is actually referenced.

        Raises
        ------
        TypeError
            If arguments are not of type str.
        """

        if not isinstance(from_object_class_name, str) or not isinstance(from_object_uuid, str) or\
            not isinstance(from_property_name, str) or not isinstance(to_object_uuid, str):
            raise TypeError('All arguments must be of type string')

        if is_weaviate_object_url(from_object_uuid):
            from_object_uuid = get_uuid_from_weaviate_url(from_object_uuid)
        if is_weaviate_object_url(to_object_uuid):
            to_object_uuid = get_uuid_from_weaviate_url(to_object_uuid)

        self._from_object_class_names.append(from_object_class_name)
        self._from_object_ids.append(from_object_uuid)
        self._from_object_properties.append(from_property_name)
        self._to_object_ids.append(to_object_uuid)

    def add_reference(self,
            from_object_uuid: str,
            from_object_class_name: str,
            from_property_name: str,
            to_object_uuid: str
        ) -> None:
        """
        'add_references' is deprecated due to redundancy, use 'add' instead!
        """

        warnings.warn(
            "'add_references' is deprecated due to redundancy, use 'add' instead!",
            DeprecationWarning
        )

        return self.add(
            from_object_uuid=from_object_uuid,
            from_object_class_name=from_object_class_name,
            from_property_name=from_property_name,
            to_object_uuid=to_object_uuid
            )

    def get_request_body(self) -> List[dict]:
        """
        Get request body as a list of dictionaries, where each dictionary
        is a weaviate-schema reference.

        Returns
        -------
        list
            A list of references as dictionaries.
        """

        batch_body = []
        for i in range(len(self)):
            batch_body.append(
                {
                "from": "weaviate://localhost/" + self._from_object_class_names[i] + "/"
                    + self._from_object_ids[i] + "/" + self._from_object_properties[i],
                "to": "weaviate://localhost/" + self._to_object_ids[i]
                }
            )
        return batch_body


class ObjectsBatchRequest(BatchRequest):
    """
    Collect objects for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def __init__(self):
        self._objects = []

    def __len__(self):
        return len(self._objects)

    def add(self,
            data_object: dict,
            class_name: str,
            uuid: str=None
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
            If an argument passed is not of an appropriate type.
        ValueError
            If 'uuid' is not of a propper form.
        """

        if not isinstance(data_object, dict):
            raise TypeError("Object must be of type dict")
        if not isinstance(class_name, str):
            raise TypeError("Class name must be of type str")

        batch_item = {
            "class": class_name,
            "properties": copy.deepcopy(data_object)
        }
        if uuid is not None:
            if not isinstance(uuid, str):
                raise TypeError("UUID must be of type str")
            if not validators.uuid(uuid):
                raise ValueError("UUID is not in a proper form")
            batch_item["id"] = uuid

        self._objects.append(batch_item)

    def add_object(self,
            data_object: dict,
            class_name: str,
            uuid: str=None
        ) -> None:
        """
        'add_object' is deprecated due to redundancy, use 'add' instead!
        """

        warnings.warn(
            "'add_object' is deprecated due to redundancy, use 'add' instead!",
            DeprecationWarning
        )

        return self.add(
            data_object=data_object,
            class_name=class_name,
            uuid=uuid
        )

    def get_request_body(self) -> dict:
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
