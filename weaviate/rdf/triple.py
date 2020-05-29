from rdflib import Graph
import weaviate
import weaviate.tools as tools
import uuid
from weaviate.rdf.constants import tripple_schema


class TripleLoader:

    def __init__(self, client):
        """

        :param client:
        :type client: weaviate.Client
        """
        self._client = client
        # To avoid adding too many of the same objects we will cache their uuids
        # This is not strictly necessary just an optimization
        self._uuid_cache = {}
        self._batcher = None

    def _add_schema(self):
        if not self._client.contains_schema(tripple_schema):
            self._client.create_schema(tripple_schema)

    def _add_rdf_object(self, value, class_name):
        """ Create the object in weaviate

        :param value: of the object
        :param class_name: either Subject, Predicate or Object
        :return: uuid of the object
        """
        object_id = tools.generate_uuid(value, class_name)
        if object_id in self._uuid_cache:
            return object_id
        self._uuid_cache[object_id] = True

        thing = {
            "value": str(value),
            "valueKey": str(value)
        }
        self._batcher.add_thing(thing, class_name, object_id)
        return object_id

    def add_graph(self, graph):
        """

        :param graph:
        :type graph: rdflib.Graph
        :return:
        """
        self._add_schema()

        self._batcher = tools.Batcher(self._client)

        for s, p, o in graph:
            s_id = self._add_rdf_object(s, "Subject")
            p_id = self._add_rdf_object(p, "Predicate")
            o_id = self._add_rdf_object(o, "Object")

            t_id = str(uuid.uuid4())
            self._batcher.add_thing({}, "Triple", t_id)
            self._batcher.add_reference("Triple", t_id, "subject", s_id)
            self._batcher.add_reference("Triple", t_id, "predicate", p_id)
            self._batcher.add_reference("Triple", t_id, "object", o_id)

        self._batcher.close()
