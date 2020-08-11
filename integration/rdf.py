import weaviate.rdf as wrdf
import weaviate as w
from rdflib import Graph
import os
import time

client = w.Client("http://localhost:8080")
t = wrdf.TripleLoader(client)
ci_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../ci")


def query(subject):
    q = """
    { Get { Things { Subject (where: {
            path: ["valueKey"]
            operator: Equal
            valueString: "%s"
          }){ value }}}}
    """
    qq = (q % subject)
    result = client.query.raw(qq)
    return result["data"]["Get"]["Things"]["Subject"]


def add_ttl_file(file_name):
    g = Graph()
    ttl_file = os.path.join(ci_folder, file_name)
    g.parse(ttl_file, format="ttl")
    t.add_graph(g)


add_ttl_file("sk8.ttl")
time.sleep(2.0)
if len(query("https://semi.technology/schema/1.0.0/Skateboard#Board")) != 1:
    exit(1)
if len(query("https://semi.technology/schema/1.0.0/SkateboardPred#hasPrice")) != 0:
    exit(2)
add_ttl_file("sk8_pred.ttl")
time.sleep(2.0)
if len(query("https://semi.technology/schema/1.0.0/SkateboardPred#hasPrice")) != 1:
    exit(3)

exit(0)
