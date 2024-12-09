"""
GraphQL `Aggregate` command.
"""

import json
from dataclasses import dataclass
from typing import List, Optional

from weaviate.util import _capitalize_first_letter, file_encoder_b64, _sanitize_str
from .filter import (
    Where,
    GraphQL,
    Filter,
    NearAudio,
    NearDepth,
    NearImage,
    NearIMU,
    NearObject,
    NearText,
    NearThermal,
    NearVector,
    NearVideo,
    MediaType,
)


@dataclass
class Hybrid:
    query: Optional[str]
    alpha: Optional[float]
    vector: Optional[List[float]]
    properties: Optional[List[str]]
    target_vectors: Optional[List[str]]
    max_vector_distance: Optional[List[str]]

    def __init__(self, content: dict) -> None:
        self.query = content.get("query")
        self.alpha = content.get("alpha")
        self.vector = content.get("vector")
        self.properties = content.get("properties")
        self.target_vectors = content.get("targetVectors")
        self.max_vector_distance = content.get("maxVectorDistance")

    def __str__(self) -> str:
        ret = ""
        if self.query is not None:
            ret += f"query: {_sanitize_str(self.query)}"
        if self.vector is not None:
            ret += f", vector: {self.vector}"
        if self.alpha is not None:
            ret += f", alpha: {self.alpha}"
        if self.properties is not None and len(self.properties) > 0:
            props = '","'.join(self.properties)
            ret += f', properties: ["{props}"]'
        if self.target_vectors is not None:
            target_vectors = '","'.join(self.target_vectors)
            ret += f', targetVectors: ["{target_vectors}"]'
        if self.max_vector_distance is not None:
            ret += f", maxVectorDistance:{self.max_vector_distance}"
        return "hybrid:{" + ret + "}"


class AggregateBuilder(GraphQL):
    """
    AggregateBuilder class used to aggregate Weaviate objects.
    """

    def __init__(self, class_name: str):
        """
        Initialize a AggregateBuilder class instance.

        Parameters
        ----------
        class_name : str
            Class name of the objects to be aggregated.
        """
        self._class_name: str = _capitalize_first_letter(class_name)
        self._object_limit: Optional[int] = None
        self._with_meta_count: bool = False
        self._fields: List[str] = []
        self._where: Optional[Where] = None
        self._group_by_properties: Optional[List[str]] = None
        self._uses_filter: bool = False
        self._near: Optional[Filter] = None
        self._tenant: Optional[str] = None
        self._limit: Optional[int] = None
        self._hybrid: Optional[Hybrid] = None

    def with_tenant(self, tenant: str) -> "AggregateBuilder":
        """Sets a tenant for the query."""
        if not isinstance(tenant, str):
            raise TypeError("tenant must be of type str")

        self._tenant = tenant
        self._uses_filter = True
        return self

    def with_meta_count(self) -> "AggregateBuilder":
        """
        Set Meta Count to True.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._with_meta_count = True
        return self

    def with_object_limit(self, limit: int) -> "AggregateBuilder":
        """
        Set objectLimit to limit vector search results used within the aggregation query
        only when with near<MEDIA> filter.

        Parameters
        ----------
        limit : int
            The object limit.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._object_limit = limit
        return self

    def with_limit(self, limit: int) -> "AggregateBuilder":
        """
        Set limit to limit the number of returned results from the aggregation query.

        Parameters
        ----------
        limit : int
            The limit.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._limit = limit
        return self

    def with_fields(self, field: str) -> "AggregateBuilder":
        """
        Include a field in the aggregate query.

        Parameters
        ----------
        field : str
            Field to include in the aggregate query.
            e.g. '<property_name> { count }'

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._fields.append(field)
        return self

    def with_where(self, content: dict) -> "AggregateBuilder":
        """
        Set 'where' filter.

        Parameters
        ----------
        content : dict
            The where filter to include in the aggregate query. See examples below.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._where = Where(content)
        self._uses_filter = True
        return self

    def with_hybrid(self, content: dict) -> "AggregateBuilder":
        """Get objects using bm25 and vector, then combine the results using a reciprocal ranking algorithm.

        Parameters
        ----------
        content : dict
            The content of the `hybrid` filter to set.
        """
        if self._near is not None:
            raise AttributeError("Cannot use 'hybrid' and 'near' filters simultaneously.")
        self._hybrid = Hybrid(content)
        self._uses_filter = True
        return self

    def with_group_by_filter(self, properties: List[str]) -> "AggregateBuilder":
        """
        Add a group by filter to the query. Might requires the user to set
        an additional group by clause using `with_fields(..)`.

        Parameters
        ----------
        properties : list of str
            list of properties that are included in the group by filter.
            Generates a filter like: 'groupBy: ["property1", "property2"]'
            from a list ["property1", "property2"]

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._group_by_properties = properties
        self._uses_filter = True
        return self

    def with_near_text(self, content: dict) -> "AggregateBuilder":
        """
        Set `nearText` filter. This filter can be used with text modules (text2vec).
        E.g.: text2vec-contextionary, text2vec-transformers.
        NOTE: The 'autocorrect' field is enabled only with the `text-spellcheck` Weaviate module.

        Parameters
        ----------
        content : dict
            The content of the `nearText` filter to set. See examples below.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        self._near = NearText(content)
        self._uses_filter = True
        return self

    def with_near_vector(self, content: dict) -> "AggregateBuilder":
        """
        Set `nearVector` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearVector` filter to set. See examples below.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        self._near = NearVector(content)
        self._uses_filter = True
        return self

    def with_near_object(self, content: dict) -> "AggregateBuilder":
        """
        Set `nearObject` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearObject` filter to set. See examples below.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        self._near = NearObject(content, True)
        self._uses_filter = True
        return self

    def with_near_image(self, content: dict, encode: bool = True) -> "AggregateBuilder":
        """
        Set `nearImage` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearImage` filter to set. See examples below.
        encode : bool, optional
            Whether to encode the `content["image"]` to base64 and convert to string. If True, the
            `content["image"]` can be an image path or a file opened in binary read mode. If False,
            the `content["image"]` MUST be a base64 encoded string (NOT bytes, i.e. NOT binary
            string that looks like this: b'BASE64ENCODED' but simple 'BASE64ENCODED').
            By default True.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            The updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """
        self._media_type = MediaType.IMAGE
        if self._near is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        if encode:
            content["image"] = file_encoder_b64(content["image"])
        self._near = NearImage(content)
        self._uses_filter = True
        return self

    def with_near_audio(self, content: dict, encode: bool = True) -> "AggregateBuilder":
        """
        Set `nearAudio` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearAudio` filter to set. See examples below.
        encode : bool, optional
            Whether to encode the `content["audio"]` to base64 and convert to string. If True, the
            `content["audio"]` can be an audio path or a file opened in binary read mode. If False,
            the `content["audio"]` MUST be a base64 encoded string (NOT bytes, i.e. NOT binary
            string that looks like this: b'BASE64ENCODED' but simple 'BASE64ENCODED').
            By default True.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            The updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.AUDIO
        if self._near is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near = NearAudio(content)
        self._uses_filter = True
        return self

    def with_near_video(self, content: dict, encode: bool = True) -> "AggregateBuilder":
        """
        Set `nearVideo` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearVideo` filter to set. See examples below.
        encode : bool, optional
            Whether to encode the `content["video"]` to base64 and convert to string. If True, the
            `content["video"]` can be an video path or a file opened in binary read mode. If False,
            the `content["video"]` MUST be a base64 encoded string (NOT bytes, i.e. NOT binary
            string that looks like this: b'BASE64ENCODED' but simple 'BASE64ENCODED').
            By default True.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            The updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.VIDEO
        if self._near is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near = NearVideo(content)
        self._uses_filter = True
        return self

    def with_near_depth(self, content: dict, encode: bool = True) -> "AggregateBuilder":
        """
        Set `nearDepth` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearDepth` filter to set. See examples below.
        encode : bool, optional
            Whether to encode the `content["depth"]` to base64 and convert to string. If True, the
            `content["depth"]` can be an depth path or a file opened in binary read mode. If False,
            the `content["depth"]` MUST be a base64 encoded string (NOT bytes, i.e. NOT binary
            string that looks like this: b'BASE64ENCODED' but simple 'BASE64ENCODED').
            By default True.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            The updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.DEPTH
        if self._near is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near = NearDepth(content)
        self._uses_filter = True
        return self

    def with_near_thermal(self, content: dict, encode: bool = True) -> "AggregateBuilder":
        """
        Set `nearThermal` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearThermal` filter to set. See examples below.
        encode : bool, optional
            Whether to encode the `content["thermal"]` to base64 and convert to string. If True, the
            `content["thermal"]` can be an thermal path or a file opened in binary read mode. If False,
            the `content["thermal"]` MUST be a base64 encoded string (NOT bytes, i.e. NOT binary
            string that looks like this: b'BASE64ENCODED' but simple 'BASE64ENCODED').
            By default True.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            The updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.THERMAL
        if self._near is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near = NearThermal(content)
        self._uses_filter = True
        return self

    def with_near_imu(self, content: dict, encode: bool = True) -> "AggregateBuilder":
        """
        Set `nearIMU` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearIMU` filter to set. See examples below.
        encode : bool, optional
            Whether to encode the `content["thermal"]` to base64 and convert to string. If True, the
            `content["thermal"]` can be an thermal path or a file opened in binary read mode. If False,
            the `content["thermal"]` MUST be a base64 encoded string (NOT bytes, i.e. NOT binary
            string that looks like this: b'BASE64ENCODED' but simple 'BASE64ENCODED').
            By default True.


        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            The updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.IMU
        if self._near is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if self._hybrid is not None:
            raise AttributeError("Cannot use 'near' and 'hybrid' filters simultaneously.")
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near = NearIMU(content)
        self._uses_filter = True
        return self

    def build(self) -> str:
        """
        Build the query and return the string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """

        # Path
        query = f"{{Aggregate{{{self._class_name}"

        # Filter
        if self._uses_filter:
            query += "("
            if self._where is not None:
                query += str(self._where)
            if self._group_by_properties is not None:
                query += f"groupBy: {json.dumps(self._group_by_properties)}"
            if self._near is not None:
                query += str(self._near)
            if self._object_limit:
                query += f"objectLimit: {self._object_limit}"
            if self._tenant is not None:
                query += f'tenant: "{self._tenant}"'
            if self._limit is not None:
                query += f"limit: {self._limit}"
            if self._hybrid is not None:
                query += str(self._hybrid)
            query += ")"

        # Body
        query += "{"
        if self._with_meta_count:
            query += "meta{count}"
        for field in self._fields:
            query += field

        # close
        query += "}}}"
        return query
