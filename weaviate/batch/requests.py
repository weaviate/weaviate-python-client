from __future__ import unicode_literals
import validators
import copy
from weaviate.util import is_weaviate_entity_url, get_uuid_from_weaviate_url
from weaviate import SEMANTIC_TYPE_THINGS


class ReferenceBatchRequest:
    """
    Collect references to add them in one request to weaviate.
    Caution this request will miss some validations to be faster.
    """

    def __init__(self):
        self._from_semantic_type = []
        self._from_entity_class_names = []
        self._from_entity_ids = []
        self._from_entity_properties = []
        self._to_entity_ids = []
        self._to_semantic_type = []

    def __len__(self):
        return len(self._from_entity_class_names)

    def get_batch_size(self):
        return len(self._from_entity_class_names)

    def add_reference(self, from_entity_uuid, from_entity_class_name, from_property_name,
                    to_entity_uuid, from_semantic_type=SEMANTIC_TYPE_THINGS, to_semantic_type=SEMANTIC_TYPE_THINGS):
        """ Add one reference to this batch

        :param from_entity_uuid: The UUID or URL of the thing that should reference another entity.
        :type from_entity_uuid: str in form of UUID
        :param from_entity_class_name: The name of the class that should reference another entity.
        :type from_entity_class_name: str
        :param from_property_name: The name of the property that contains the reference.
        :type from_property_name: str
        :param to_entity_uuid: The UUID or URL of the thing that is actually referenced.
        :type to_entity_uuid: str
        :param from_semantic_type: Either things or actions.
                                   Defaults to things.
                                   Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type from_semantic_type: str
        :param to_semantic_type: Either things or actions.
                                 Defaults to things.
                                 Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type to_semantic_type: str
        :return: None if successful
        :raises:
            TypeError: If arguments are not string.
        """

        if not isinstance(from_semantic_type, str) or not isinstance(from_entity_class_name, str) or \
                not isinstance(from_entity_uuid, str) or not isinstance(from_property_name, str) or \
                not isinstance(to_semantic_type, str) or not isinstance(to_entity_uuid, str):
            raise TypeError('All arguments must be of type string')

        if is_weaviate_entity_url(from_entity_uuid):
            from_entity_uuid = get_uuid_from_weaviate_url(from_entity_uuid)
        if is_weaviate_entity_url(to_entity_uuid):
            to_entity_uuid = get_uuid_from_weaviate_url(to_entity_uuid)

        self._from_semantic_type.append(from_semantic_type)
        self._from_entity_class_names.append(from_entity_class_name)
        self._from_entity_ids.append(from_entity_uuid)
        self._from_entity_properties.append(from_property_name)
        self._to_semantic_type.append(to_semantic_type)
        self._to_entity_ids.append(to_entity_uuid)

    def get_request_body(self):
        batch_body = [None] * self.get_batch_size()
        for i in range(self.get_batch_size()):
            batch_body[i] = {
                "from": "weaviate://localhost/"+self._from_semantic_type[i]+"/" +
                        self._from_entity_class_names[i]+"/"+self._from_entity_ids[i] +
                        "/"+self._from_entity_properties[i],
                "to": "weaviate://localhost/"+self._to_semantic_type[i]+"/"+self._to_entity_ids[i]
            }
        return batch_body


class EntityBatchRequest(object):
    """
        Base for storing entities
    """

    def __init__(self):
        self._entities = []

    def __len__(self):
        return len(self._entities)

    def _add_entity(self, entity, class_name, uuid=None):

        if not isinstance(entity, dict):
            raise TypeError("Thing must be of type dict")
        if not isinstance(class_name, str):
            raise TypeError("Class name must be of type str")

        batch_item = {
            "class": class_name,
            "schema": copy.deepcopy(entity)
        }
        if uuid is not None:
            if not isinstance(uuid, str):
                raise TypeError("UUID must be of type str")
            if not validators.uuid(uuid):
                raise ValueError("UUID is not in a proper form")
            batch_item["id"] = uuid

        self._entities.append(batch_item)


class ThingsBatchRequest(EntityBatchRequest):
    """
    Collect things for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def __init__(self):
        super(ThingsBatchRequest, self).__init__()

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
        self._add_entity(thing, class_name, uuid)

    def get_request_body(self):
        """ Get the request body as it is needed for weaviate

        :return: the request body as a dict
        """
        return {
            "fields": [
                "ALL"
            ],
            "things": self._entities
        }


class ActionsBatchRequest(EntityBatchRequest):
    """
    Collect things for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def __init__(self):
        super(ActionsBatchRequest, self).__init__()

    def add_action(self, action, class_name, uuid=None):
        """ Add an action to this batch

        :param action: that should be added as part of the batch.
        :type action: dict
        :param class_name: class of the action.
        :type class_name: str
        :param uuid: if given the thing will be added under this uuid.
        :type uuid: str
        :raises: TypeError, ValueError
        """
        self._add_entity(action, class_name, uuid)

    def get_request_body(self):
        """ Get the request body as it is needed for weaviate

        :return: the request body as a dict
        """
        return {
            "fields": [
                "ALL"
            ],
            "actions": self._entities
        }
