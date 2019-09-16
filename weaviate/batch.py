

class ReferenceBatchRequest:

    def __init__(self):
        self.from_thing_class_names = []
        self.from_thing_ids = []
        self.from_thing_properties = []
        self.to_thing_ids = []

    def add_reference(self, from_thing_class_name, from_thing_uuid, from_thing_property, to_thing_uuid):

        if not isinstance(from_thing_class_name, str) or not isinstance(from_thing_uuid, str) or \
                not isinstance(from_thing_property, str) or not isinstance(to_thing_uuid, str):
            raise ValueError('All arguments must be of type string')

        self.from_thing_class_names.append(from_thing_class_name)
        self.from_thing_ids.append(from_thing_uuid)
        self.from_thing_properties.append(from_thing_property)
        self.to_thing_ids.append(to_thing_uuid)

    def get_batch_size(self):
        return len(self.from_thing_class_names)

    def get_request_body(self):
        batch_body = [None] * self.get_batch_size()
        for i in range(self.get_batch_size()):
            batch_body[i] = {
                "from": "weaviate://localhost/things/" + self.from_thing_class_names[i] + "/" + self.from_thing_ids[i] + "/" +
                        self.from_thing_properties[i],
                "to": "weaviate://localhost/things/" + self.to_thing_ids[i]
            }
        return batch_body