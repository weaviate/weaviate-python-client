import time
import weaviate

from integration.integration_util import testmethod


schema = {
    "classes": [
        {
            "class": "ClassA",
            "properties": [
                {
                    "dataType": [
                        "string"
                    ],
                    "name": "stringProp"
                },
                {
                    "dataType": [
                        "int"
                    ],
                    "name": "intProp"
                }
            ]
        }
    ]
}

class TestMisc:
    def __init__(self, client: weaviate.Client):
        client.schema.delete_all()
        self.client = client
        self.git_hash = "2147e86"
        self.server_version = "1.15.4"
        self.num_objects = 10
        self.node_name = "node1"

    def test(self):
        self._get_nodes_status_without_data()
        self._get_nodes_status_with_data()
        self._log("done!")

    def _get_nodes_status_without_data(self):
        self._log("get nodes status without data")
        resp = self.client.misc.get_nodes_status()
        assert len(resp) == 1
        assert resp[0]["gitHash"] == self.git_hash
        assert resp[0]["name"] == self.node_name
        assert len(resp[0]["shards"]) == 0
        assert resp[0]["stats"]["objectCount"] == 0
        assert resp[0]["stats"]["shardCount"] == 0
        assert resp[0]["status"] == "HEALTHY"
        assert resp[0]["version"] == self.server_version

    @testmethod
    def _get_nodes_status_with_data(self):
        self._log("get nodes status with data")
        class_name = "ClassA"
        resp = self.client.misc.get_nodes_status()
        assert len(resp) == 1
        assert resp[0]["gitHash"] == self.git_hash
        assert resp[0]["name"] == self.node_name
        assert len(resp[0]["shards"]) == 1
        assert resp[0]["shards"][0]["class"] == class_name
        assert resp[0]["shards"][0]["objectCount"] == self.num_objects
        assert resp[0]["stats"]["objectCount"] == self.num_objects
        assert resp[0]["stats"]["shardCount"] == 1
        assert resp[0]["status"] == "HEALTHY"
        assert resp[0]["version"] == self.server_version
    
    def _setup(self):
        self.client.schema.create(schema)
        for i in range(self.num_objects):
            self.client.data_object.create({"stringProp": f"object-{i}", "intProp": i}, "ClassA")
        time.sleep(2.0)
    
    def _cleanup(self):
        for _, cls in enumerate(schema["classes"]):
            self.client.schema.delete_class(cls["class"])

    def _log(self, msg):
        print(f"TestMisc: {msg}")


if __name__ == "__main__":
    client = weaviate.Client("http://localhost:8080")
    misc = TestMisc(client)
    misc.test()
