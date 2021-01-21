import os
import time
import sys
import weaviate.rdf as wrdf
import weaviate
from rdflib import Graph
from integration.integration_util import TestFailedException

client = weaviate.Client("http://localhost:8080")
t = wrdf.TripleLoader(client)
ci_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../ci")


def query(subject):
    q = """
    { Get { Subject (where: {
            path: ["valueKey"]
            operator: Equal
            valueString: "%s"
          }){ value }}}
    """
    qq = (q % subject)
    result = client.query.raw(qq)
    return result["data"]["Get"]["Subject"]


def add_ttl_file(file_name):
    g = Graph()
    ttl_file = os.path.join(ci_folder, file_name)
    g.parse(ttl_file, format="ttl")
    t.add_graph(g)

def test_length():
    add_ttl_file("sk8.ttl")
    time.sleep(2.0)
    if len(query("https://semi.technology/schema/1.0.0/Skateboard#Board")) != 1:
        raise TestFailedException("Wrong number of objects")
    if len(query("https://semi.technology/schema/1.0.0/SkateboardPred#hasPrice")) != 0:
        raise TestFailedException("Wrong number of objects")
    add_ttl_file("sk8_pred.ttl")
    time.sleep(2.0)
    if len(query("https://semi.technology/schema/1.0.0/SkateboardPred#hasPrice")) != 1:
        raise TestFailedException("Wrong number of objects")
    return 0

if __name__ == "__main__":
    test_length()
