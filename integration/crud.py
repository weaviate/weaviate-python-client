import time
import weaviate

from datetime import datetime
from datetime import timezone
from integration.integration_util import TestFailedException

def get_query_for_group(name):
    return ("""
    {
      Get {
        Group (where: {
          path: ["name"]
          operator: Equal
          valueText: "%s"
        }) {
          name
          _additional {
            id
          }
          members {
            ... on Person {
              name
              _additional {
                id
              }
            }
          }
        }
      }
    }
    """ % name)


class IntegrationTestCrud:

    def __init__(self, client):
        """

        :param client: is expected to already have the schema loaded
        :type client: weaviate.Client
        """
        if not client.schema.contains():
            raise TestFailedException("Integration test crud requires a schema to be loaded.")
        self.client = client
        self.chemists = [None] * 3

    def test_crud(self):
        self._create_objects_batch()
        self._create_objects()
        time.sleep(2.0)
        self._create_references()
        time.sleep(2.0)
        self._validate_data_loading()
        self._delete_objects()

        self._delete_references()
        self._get_data()

    def _create_objects_batch(self):
        print("Create a batch with data.")
        

        self.client.batch.add_data_object({"name": "John Rawls"}, "Person")
        self.client.batch.add_data_object({"name": "Emanuel Kant"}, "Person")
        self.client.batch.add_data_object({"name": "Plato"}, "Person")
        self.client.batch.add_data_object({"name": "Pull-up"}, "Exercise")
        self.client.batch.add_data_object({"name": "Squat"}, "Exercise")
        self.client.batch.add_data_object({"name": "Star jump"}, "Exercise")

        print("Load batch.")
        self.client.batch.create_objects()

    def _create_objects(self):
        print("Load a single objects.")
        self.client.data_object.create({"name": "Andrew S. Tanenbaum"}, "Person", "28954261-0449-57a2-ade5-e9e08d11f51a")
        self.client.data_object.create({"name": "Alan Turing"}, "Person", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.client.data_object.create({"name": "John von Neumann"}, "Person", "b36268d4-a6b5-5274-985f-45f13ce0c642")
        self.client.data_object.create({"name": "Tim Berners-Lee"}, "Person", "d1e90d26-d82e-5ef8-84f6-ca67119c7998")
        self.client.data_object.create({"name": "Legends"}, "Group", "2db436b5-0557-5016-9c5f-531412adf9c6")
        self.client.data_object.create({"name": "Chemists"}, "Group", "577887c1-4c6b-5594-aa62-f0c17883d9bf")

        self.chemists[0] = self.client.data_object.create({"name": "Marie Curie"}, "Person")
        self.chemists[1] = self.client.data_object.create({"name": "Fritz Haber"}, "Person")
        self.chemists[2] = self.client.data_object.create({"name": "Walter White"}, "Person")

        local_time = datetime.now(timezone.utc).astimezone()
        self.client.data_object.create({"start": local_time.isoformat()}, "Call",
                             "3ab05e06-2bb2-41d1-b5c5-e044f3aa9623")

    def _create_references(self):
        print("Add reference to object.")
        self.client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members",
                                    "b36268d4-a6b5-5274-985f-45f13ce0c642")
        self.client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members",
                                    "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        print("Add reference to object in batch.")

        for chemist in self.chemists:
            self.client.batch.add_reference("577887c1-4c6b-5594-aa62-f0c17883d9bf", "Group", "members",
                                          chemist)

        self.client.batch.create_references()

    def _validate_data_loading(self):
        print("Validate if loading was successful")
        legends = self.client.query.raw(get_query_for_group("Legends"))['data']['Get']
        for member in legends["Group"][0]["members"]:
            if not member["name"] in ["John von Neumann", "Alan Turing"]:
                raise TestFailedException("Adding references to objects failed")

        group_chemists = self.client.query.raw(get_query_for_group("Chemists"))['data']['Get']
        for member in group_chemists["Group"][0]["members"]:
            if not member["name"] in ["Marie Curie", "Fritz Haber", "Walter White"]:
                raise TestFailedException("Adding references to objects failed")
        if len(group_chemists["Group"][0]["members"]) != 3:
            raise TestFailedException("Lengths of the `Group` do not match!")

    def _delete_objects(self):
        print("Test Delete")
        self.client.data_object.delete(self.chemists[2])  # Delete Walter White not a real chemist just a legend
        time.sleep(1.1)
        if self.client.data_object.exists(self.chemists[2]):
            raise TestFailedException("Thing was not correctly deleted")

    def _delete_references(self):
        # Test delete reference
        prime_ministers_group = self.client.data_object.create({"name": "Prime Ministers"}, "Group")
        prime_ministers = []
        prime_minister_names = ["Wim Kok", "Dries van Agt", "Piet de Jong"]
        for name in prime_minister_names:
            prime_ministers.append(self.client.data_object.create({"name": name}, "Person"))
        time.sleep(2.0)
        for prime_minister in prime_ministers:
            self.client.data_object.reference.add(prime_ministers_group, "members", prime_minister)
        time.sleep(2.0)
        self.client.data_object.reference.delete(prime_ministers_group, "members", prime_ministers[0])
        time.sleep(2.0)
        prime_ministers_group_object = self.client.data_object.get_by_id(prime_ministers_group)
        if len(prime_ministers_group_object["properties"]["members"]) != 2:
            raise TestFailedException("Reference not deleted correctly")

    def _get_data(self):
        self.client.data_object.create({"name": "George Floyd"}, "Person", "452e3031-bdaa-4468-9980-aed60d0258bf")
        time.sleep(2.0)
        person = self.client.data_object.get_by_id("452e3031-bdaa-4468-9980-aed60d0258bf", ["interpretation"], with_vector=True)
        print(person)

        if "vector" not in person:
            raise TestFailedException("additional property _vector not in person")
        if "interpretation" not in person["additional"]:
            raise TestFailedException("additional property _interpretation not in person")

        persons = self.client.data_object.get(with_vector=True)
        if "vector" not in persons["objects"][0]:
            raise TestFailedException("additional property _vector not in persons")