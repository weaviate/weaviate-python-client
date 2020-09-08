import weaviate
from datetime import datetime
from datetime import timezone
import time
from integration.queries import *


class IntegrationTestCrud:

    def __init__(self, client):
        """

        :param client: is expected to already have the schema loaded
        :type client: weaviate.Client
        """
        if not client.schema.contains():
            raise Exception("Integration test crud requires a schema to be loaded")
        self.client = client
        self.chemists = [None] * 3

    def test_crud(self):
        self._create_objects_batch()
        self._create_objects()
        time.sleep(2.0)
        self._add_references()
        time.sleep(2.0)
        self._validate_data_loading()
        self._delete_objects()

        self._delete_references()
        self._get_data()

    def _create_objects_batch(self):
        print("Create a batch with data")
        things_batch = weaviate.batch.ThingsBatchRequest()

        things_batch.add_thing({"name": "John Rawls"}, "Person")
        things_batch.add_thing({"name": "Emanuel Kant"}, "Person")
        things_batch.add_thing({"name": "Plato"}, "Person")

        actions_batch = weaviate.batch.ActionsBatchRequest()
        actions_batch.add_action({"name": "Pull-up"}, "Exercise")
        actions_batch.add_action({"name": "Squat"}, "Exercise")
        actions_batch.add_action({"name": "Star jump"}, "Exercise")

        print("Load batch")
        self.client.batch.create_things(things_batch)
        self.client.batch.create_actions(actions_batch)

    def _create_objects(self):
        print("Load a single things and actions")
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
                             "3ab05e06-2bb2-41d1-b5c5-e044f3aa9623", weaviate.SEMANTIC_TYPE_ACTIONS)

    def _add_references(self):
        print("Add reference to thing")
        self.client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members",
                                    "b36268d4-a6b5-5274-985f-45f13ce0c642")
        self.client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members",
                                    "1c9cd584-88fe-5010-83d0-017cb3fcb446")

        print("Add reference to thing in batch")
        reference_batch = weaviate.batch.ReferenceBatchRequest()

        for chemist in self.chemists:
            reference_batch.add_reference("577887c1-4c6b-5594-aa62-f0c17883d9bf", "Group", "members",
                                          chemist)

        self.client.batch.add_references(reference_batch)

    def _validate_data_loading(self):
        print("Validate if loading was successful")
        legends = self.client.query.raw(gql_get_group_legends)
        legends = things_of_result(legends)
        for member in legends["Group"][0]["Members"]:
            if not member["name"] in ["John von Neumann", "Alan Turing"]:
                print("Adding references to things failed")
                exit(5)

        group_chemists = self.client.query.raw(gql_get_group_chemists)
        group_chemists = things_of_result(group_chemists)
        for member in group_chemists["Group"][0]["Members"]:
            if not member["name"] in ["Marie Curie", "Fritz Haber", "Walter White"]:
                print("Adding references to things failed")
                exit(6)
        if len(group_chemists["Group"][0]["Members"]) != 3:
            exit(7)


    def _delete_objects(self):
        print("Test Delete")
        self.client.data_object.delete(self.chemists[2])  # Delete Walter White not a real chemist just a legend
        time.sleep(1.1)
        if self.client.data_object.get_by_id(self.chemists[2]) is not None:
            print("Thing was not correctly deleted")
            exit(8)

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
        if len(prime_ministers_group_object["schema"]["members"]) != 2:
            print("Reference not deleted correctly")
            exit(9)

    def _get_data(self):
        self.client.data_object.create({"name": "George Floyd"}, "Person", "452e3031-bdaa-4468-9980-aed60d0258bf")
        time.sleep(2.0)
        person = self.client.data_object.get_by_id("452e3031-bdaa-4468-9980-aed60d0258bf", ["_vector", "_interpretation"])
        if "_vector" not in person:
            print("underscore property _vector not in person")
            exit(10)
        if "_interpretation" not in person:
            print("underscore property _interpretation not in person")
            exit(11)

        persons = self.client.data_object.get(["_vector"])
        if "_vector" not in persons[0]:
            print("underscore property _vector not in persons")
            exit(12)