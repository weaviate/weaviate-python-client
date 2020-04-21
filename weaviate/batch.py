from __future__ import unicode_literals
import validators
import copy
from weaviate.util import is_weaviate_thing_url, get_uuid_from_weaviate_url


class ReferenceBatchRequest:
    """
    Collect references to add them in one request to weaviate.
    Caution this request will miss some validations to be faster.
    """

    def __init__(self):
        self._from_thing_class_names = []
        self._from_thing_ids = []
        self._from_thing_properties = []
        self._to_thing_ids = []

    def __len__(self):
        return len(self._from_thing_class_names)

    def add_reference(self, from_thing_class_name, from_thing_uuid, from_property_name, to_thing_uuid):
        """ Add one reference to this batch

        :param from_thing_class_name: The name of the class that should reference another thing.
        :type from_thing_class_name: str
        :param from_thing_uuid: The UUID or URL of the thing that should reference another thing.
        :type from_thing_uuid: str in form of UUID
        :param from_property_name: The name of the property that contains the reference.
        :type from_property_name: str
        :param to_thing_uuid: The UUID or URL of the thing that is actually referenced.
        :type to_thing_uuid: str
        :return: None if successful
        :raises:
            TypeError: If arguments are not string.
        """

        if not isinstance(from_thing_class_name, str) or not isinstance(from_thing_uuid, str) or \
                not isinstance(from_property_name, str) or not isinstance(to_thing_uuid, str):
            raise TypeError('All arguments must be of type string')

        if is_weaviate_thing_url(from_thing_uuid):
            from_thing_uuid = get_uuid_from_weaviate_url(from_thing_uuid)
        if is_weaviate_thing_url(to_thing_uuid):
            to_thing_uuid = get_uuid_from_weaviate_url(to_thing_uuid)


        self._from_thing_class_names.append(from_thing_class_name)
        self._from_thing_ids.append(from_thing_uuid)
        self._from_thing_properties.append(from_property_name)
        self._to_thing_ids.append(to_thing_uuid)

    def get_batch_size(self):
        return len(self._from_thing_class_names)

    def get_request_body(self):
        batch_body = [None] * self.get_batch_size()
        for i in range(self.get_batch_size()):
            batch_body[i] = {
                "from": "weaviate://localhost/things/" + self._from_thing_class_names[i] + "/" + self._from_thing_ids[i] + "/" +
                        self._from_thing_properties[i],
                "to": "weaviate://localhost/things/" + self._to_thing_ids[i]
            }
        return batch_body


class ThingsBatchRequest:
    """
    Collect things for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def __init__(self):
        self._things = []

    def __len__(self):
        return len(self._things)

    def add_thing(self, thing, class_name, uuid=None):
        """ Add a thing to this batch

        :param thing: that should be added as part of the batch.
        :type thing: dict
        :param class_name: class of the thing.
        :type class_name: str
        :param uuid: if given the thing will be added under this uuid.
        :type uuid: str
        :raises: TypeError, ValueError
        """
        if not isinstance(thing, dict):
            raise TypeError("Thing must be of type dict")
        if not isinstance(class_name, str):
            raise TypeError("Class name must be of type str")

        batch_item = {
            "class": class_name,
            "schema": copy.deepcopy(thing)
        }
        if uuid is not None:
            if not isinstance(uuid, str):
                raise TypeError("UUID must be of type str")
            if not validators.uuid(uuid):
                raise ValueError("UUID is not in a proper form")
            batch_item["id"] = uuid

        self._things.append(batch_item)

    def get_request_body(self):
        """ Get the request body as it is needed for weaviate

        :return: the request body as a dict
        """
        return {
            "fields": [
                "ALL"
            ],
            "things": self._things
        }
