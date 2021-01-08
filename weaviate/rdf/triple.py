import uuid
from typing import Any
import rdflib
import weaviate
import weaviate.tools as tools
from weaviate.rdf.constants import triple_schema


class TripleLoader:

    def __init__(self, client: weaviate.Client):
        """
        Initialize a TripleLoader class instance.

        Parameters
        ----------
        client : weaviate.Client
            An active instance of weaviate client.
        """

        self._client = client
        # To avoid adding too many of the same objects we will cache their uuids
        # This is not strictly necessary just an optimization
        self._uuid_cache = {}
        self._batcher = None

    def _add_schema(self) -> None:
        """
        Add schema to weaviate.
        """
        if not self._client.schema.contains(triple_schema):
            self._client.schema.create(triple_schema)

    def _add_rdf_object(self, value: Any, class_name: str) -> str:
        """
        Create the object in weaviate.

        Parameters
        ----------
        value: any
            Value of the object.
        class_name : str
            Either Subject, Predicate or Object.

        Returns
        -------
        str
            The UUID of the object.
        """

        object_id = tools.generate_uuid(value, class_name)
        if object_id in self._uuid_cache:
            return object_id
        self._uuid_cache[object_id] = True

        object_ = {
            "value": str(value),
            "valueKey": str(value)
        }
        self._batcher.add_data_object(object_, class_name, object_id)
        return object_id

    def add_graph(self, graph: rdflib.Graph) -> None:
        """
        Add RDF graph to weaviate.

        Parameters
        ----------
        graph : rdflib.Graph
            The RDF graph to be added.
        """

        self._add_schema()

        self._batcher = tools.Batcher(self._client)

        for s, p, o in graph:
            s_id = self._add_rdf_object(s, "Subject")
            p_id = self._add_rdf_object(p, "Predicate")
            o_id = self._add_rdf_object(o, "Object")

            t_id = str(uuid.uuid4())
            self._batcher.add_data_object({}, "Triple", t_id)
            self._batcher.add_reference("Triple", t_id, "subject", s_id)
            self._batcher.add_reference("Triple", t_id, "predicate", p_id)
            self._batcher.add_reference("Triple", t_id, "object", o_id)
        self._batcher.close()
