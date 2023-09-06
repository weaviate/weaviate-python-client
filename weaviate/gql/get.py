"""
GraphQL `Get` command.
"""
from dataclasses import dataclass, Field, fields
from enum import Enum
from json import dumps
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from weaviate import util
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import AdditionalPropertiesException
from weaviate.gql.filter import (
    Where,
    NearText,
    NearVector,
    GraphQL,
    NearObject,
    Filter,
    Ask,
    NearImage,
    NearVideo,
    NearAudio,
    NearThermal,
    NearDepth,
    NearIMU,
    MediaType,
    Sort,
)
from weaviate.types import UUID
from weaviate.util import (
    image_encoder_b64,
    _capitalize_first_letter,
    get_valid_uuid,
    file_encoder_b64,
    BaseEnum,
)
from weaviate.warnings import _Warnings

try:
    from weaviate_grpc import weaviate_pb2
    import grpc
except ImportError:
    pass


@dataclass
class BM25:
    query: str
    properties: Optional[List[str]]

    def __str__(self) -> str:
        ret = f"query: {util._sanitize_str(self.query)}"
        if self.properties is not None and len(self.properties) > 0:
            props = '","'.join(self.properties)
            ret += f', properties: ["{props}"]'
        return "bm25:{" + ret + "}"


class HybridFusion(str, BaseEnum):
    RANKED = "rankedFusion"
    RELATIVE_SCORE = "relativeScoreFusion"


@dataclass
class Hybrid:
    query: str
    alpha: Optional[float]
    vector: Optional[List[float]]
    properties: Optional[List[str]]
    fusion_type: Optional[HybridFusion]

    def __str__(self) -> str:
        ret = f"query: {util._sanitize_str(self.query)}"
        if self.vector is not None:
            ret += f", vector: {self.vector}"
        if self.alpha is not None:
            ret += f", alpha: {self.alpha}"
        if self.properties is not None and len(self.properties) > 0:
            props = '","'.join(self.properties)
            ret += f', properties: ["{props}"]'
        if self.fusion_type is not None:
            if isinstance(self.fusion_type, Enum):
                ret += f", fusionType: {self.fusion_type.value}"
            else:
                ret += f", fusionType: {self.fusion_type}"

        return "hybrid:{" + ret + "}"


@dataclass
class GroupBy:
    path: List[str]
    groups: int
    objects_per_group: int

    def __str__(self) -> str:
        props = '","'.join(self.path)
        return f'groupBy:{{path:["{props}"], groups:{self.groups}, objectsPerGroup:{self.objects_per_group}}}'


@dataclass
class LinkTo:
    link_on: str
    linked_class: str
    properties: List[Union[str, "LinkTo"]]

    def __str__(self) -> str:
        props = " ".join(str(x) for x in self.properties)
        return self.link_on + "{... on " + self.linked_class + "{" + props + "}}"


PROPERTIES = Union[List[Union[str, LinkTo]], str]


@dataclass
class AdditionalProperties:
    uuid: bool = False
    vector: bool = False
    creationTimeUnix: bool = False
    lastUpdateTimeUnix: bool = False
    distance: bool = False
    certainty: bool = False
    score: bool = False
    explainScore: bool = False

    def __str__(self) -> str:
        additional_props: List[str] = []
        cls_fields: Tuple[Field, ...] = fields(self.__class__)
        for field in cls_fields:
            if issubclass(field.type, bool):
                enabled: bool = getattr(self, field.name)
                if enabled:
                    name = field.name
                    if field.name == "uuid":  # id is reserved python name
                        name = "id"
                    additional_props.append(name)
        if len(additional_props) > 0:
            return " _additional{" + " ".join(additional_props) + "} "
        else:
            return ""


class GetBuilder(GraphQL):
    """
    GetBuilder class used to create GraphQL queries.
    """

    def __init__(self, class_name: str, properties: Optional[PROPERTIES], connection: Connection):
        """
        Initialize a GetBuilder class instance.

        Parameters
        ----------
        class_name : str
            Class name of the objects to interact with.
        properties : str or list of str
            Properties of the objects to interact with.
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.

        Raises
        ------
        TypeError
            If argument/s is/are of wrong type.
        """

        super().__init__(connection)

        if not isinstance(class_name, str):
            raise TypeError(f"class name must be of type str but was {type(class_name)}")
        if properties is None:
            properties = []
        if isinstance(properties, str):
            properties = [properties]
        if not isinstance(properties, list):
            raise TypeError(
                "properties must be of type str, " f"list of str or None but was {type(properties)}"
            )

        self._properties: List[Union[str, LinkTo]] = []
        for prop in properties:
            if not isinstance(prop, str) and not isinstance(prop, LinkTo):
                raise TypeError("All the `properties` must be of type `str` or Reference!")
            self._properties.append(prop)

        self._class_name: str = _capitalize_first_letter(class_name)
        self._additional: dict = {"__one_level": set()}
        # '__one_level' refers to the additional properties that are just a single word, not a dict
        # thus '__one_level', only one level of complexity
        self._additional_dataclass: Optional[AdditionalProperties] = None
        self._where: Optional[Where] = None  # To store the where filter if it is added
        self._limit: Optional[int] = None  # To store the limit filter if it is added
        self._offset: Optional[str] = None  # To store the offset filter if it is added
        self._after: Optional[str] = None  # To store the offset filter if it is added
        self._near_clause: Optional[
            Filter
        ] = None  # To store the `near`/`ask` clause if it is added
        self._contains_filter = False  # true if any filter is added
        self._sort: Optional[Sort] = None
        self._bm25: Optional[BM25] = None
        self._hybrid: Optional[Hybrid] = None
        self._group_by: Optional[GroupBy] = None
        self._alias: Optional[str] = None
        self._tenant: Optional[str] = None
        self._autocut: Optional[int] = None
        self._consistency_level: Optional[str] = None

    def with_autocut(self, autocut: int) -> "GetBuilder":
        """Cuts off irrelevant results based on "jumps" in scores."""
        if not isinstance(autocut, int):
            raise TypeError("autocut must be of type int")

        self._autocut = autocut
        self._contains_filter = True
        return self

    def with_tenant(self, tenant: str) -> "GetBuilder":
        """Sets a tenant for the query."""
        if not isinstance(tenant, str):
            raise TypeError("tenant must be of type str")

        self._tenant = tenant
        self._contains_filter = True
        return self

    def with_after(self, after_uuid: UUID) -> "GetBuilder":
        """Can be used to extract all elements by giving the last ID from the previous "page".

        Requires limit to be set but cannot be combined with any other filters or search. Part of the Cursor API.
        """
        if not isinstance(after_uuid, UUID.__args__):  # type: ignore # __args__ is workaround for python 3.8
            raise TypeError("after_uuid must be of type UUID (str or uuid.UUID)")

        self._after = f'after: "{get_valid_uuid(after_uuid)}"'
        self._contains_filter = True
        return self

    def with_where(self, content: dict) -> "GetBuilder":
        """
        Set `where` filter.

        Parameters
        ----------
        content : dict
            The content of the `where` filter to set. See examples below.

        Examples
        --------
        The `content` prototype is like this:

        >>> content = {
        ...     'operator': '<operator>',
        ...     'operands': [
        ...         {
        ...             'path': [path],
        ...             'operator': '<operator>'
        ...             '<valueType>': <value>
        ...         },
        ...         {
        ...             'path': [<matchPath>],
        ...             'operator': '<operator>',
        ...             '<valueType>': <value>
        ...         }
        ...     ]
        ... }

        This is a complete `where` filter but it does not have to be like this all the time.

        Single operand:

        >>> content = {
        ...     'path': ["wordCount"],    # Path to the property that should be used
        ...     'operator': 'GreaterThan',  # operator
        ...     'valueInt': 1000       # value (which is always = to the type of the path property)
        ... }

        Or

        >>> content = {
        ...     'path': ["id"],
        ...     'operator': 'Equal',
        ...     'valueString': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf"
        ... }

        Multiple operands:

        >>> content = {
        ...     'operator': 'And',
        ...     'operands': [
        ...         {
        ...             'path': ["wordCount"],
        ...             'operator': 'GreaterThan',
        ...             'valueInt': 1000
        ...         },
        ...         {
        ...             'path': ["wordCount"],
        ...             'operator': 'LessThan',
        ...             'valueInt': 1500
        ...         }
        ...     ]
        ... }

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.
        """

        self._where = Where(content)
        self._contains_filter = True
        return self

    @property
    def name(self) -> str:
        return self._alias if self._alias else self._class_name

    def with_near_text(self, content: dict) -> "GetBuilder":
        """
        Set `nearText` filter. This filter can be used with text modules (text2vec).
        E.g.: text2vec-contextionary, text2vec-transformers.
        NOTE: The 'autocorrect' field is enabled only with the `text-spellcheck` Weaviate module.

        Parameters
        ----------
        content : dict
            The content of the `nearText` filter to set. See examples below.

        Examples
        --------
        Content full prototype:

        >>> content = {
        ...     'concepts': <list of str or str>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'moveAwayFrom': { # Optional
        ...         'concepts': <list of str or str>,
        ...         'force': <float>
        ...     },
        ...     'moveTo': { # Optional
        ...         'concepts': <list of str or str>,
        ...         'force': <float>
        ...     },
        ...     'autocorrect': <bool>, # Optional
        ... }

        Full content:

        >>> content = {
        ...     'concepts': ["fashion"],
        ...     'certainty': 0.7, # or 'distance'
        ...     'moveAwayFrom': {
        ...         'concepts': ["finance"],
        ...         'force': 0.45
        ...     },
        ...     'moveTo': {
        ...         'concepts': ["haute couture"],
        ...         'force': 0.85
        ...     },
        ...     'autocorrect': True
        ... }

        Partial content:

        >>> content = {
        ...     'concepts': ["fashion"],
        ...     'certainty': 0.7, # or 'distance'
        ...     'moveTo': {
        ...         'concepts': ["haute couture"],
        ...         'force': 0.85
        ...     }
        ... }

        Minimal content:

        >>> content = {
        ...     'concepts': "fashion"
        ... }

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_clause = NearText(content)
        self._contains_filter = True
        return self

    def with_near_vector(self, content: dict) -> "GetBuilder":
        """
        Set `nearVector` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearVector` filter to set. See examples below.

        Examples
        --------
        Content full prototype:

        >>> content = {
        ...     'vector' : <list of float>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        NOTE: Supported types for 'vector' are `list`, 'numpy.ndarray`, `torch.Tensor`
                and `tf.Tensor`.

        Full content:

        >>> content = {
        ...     'vector' : [.1, .2, .3, .5],
        ...     'certainty': 0.75, # or 'distance'
        ... }

        Minimal content:

        >>> content = {
        ...     'vector' : [.1, .2, .3, .5]
        ... }

        Or

        >>> content = {
        ...     'vector' : torch.tensor([.1, .2, .3, .5])
        ... }

        Or

        >>> content = {
        ...     'vector' : torch.tensor([[.1, .2, .3, .5]]) # it is going to be squeezed.
        ... }

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_clause = NearVector(content)
        self._contains_filter = True
        return self

    def with_near_object(self, content: dict) -> "GetBuilder":
        """
        Set `nearObject` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearObject` filter to set. See examples below.

        Examples
        --------
        Content prototype:

        >>> {
        ...     'id': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }
        >>> # alternatively
        >>> {
        ...     'beacon': "weaviate://localhost/ClassName/e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf"
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        is_server_version_14 = self._connection.server_version >= "1.14"

        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_clause = NearObject(content, is_server_version_14)
        self._contains_filter = True
        return self

    def with_near_image(self, content: dict, encode: bool = True) -> "GetBuilder":
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

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'image': <str or binary read file>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'image': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance'
        ... }

        With `encoded` True:

        >>> content = {
        ...     'image': "my_image_path.png",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Image', 'description')\\
        ...     .with_near_image(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_image_file = open("my_image_path.png", "br")
        >>> content = {
        ...     'image': my_image_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Image', 'description')\\
        ...     .with_near_image(content, encode=True) # <- encode MUST be set to True
        >>> my_image_file.close()

        With `encoded` False:

        >>> from weaviate.util import image_encoder_b64, image_decoder_b64
        >>> encoded_image = image_encoder_b64("my_image_path.png")
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Image', 'description')\\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import image_encoder_b64, image_decoder_b64
        >>> with open("my_image_path.png", "br") as my_image_file:
        ...     encoded_image = image_encoder_b64(my_image_file)
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Image', 'description')\\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

        Encode Image yourself:

        >>> import base64
        >>> with open("my_image_path.png", "br") as my_image_file:
        ...     encoded_image = base64.b64encode(my_image_file.read()).decode("utf-8")
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Image', 'description')\\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if encode:
            content["image"] = image_encoder_b64(content["image"])
        self._near_clause = NearImage(content)
        self._contains_filter = True
        return self

    def with_near_audio(self, content: dict, encode: bool = True) -> "GetBuilder":
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

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'audio': <str or binary read file>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'audio': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance'
        ... }

        With `encoded` True:

        >>> content = {
        ...     'audio': "my_audio_path.wav",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Audio', 'description')\\
        ...     .with_near_audio(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_audio_file = open("my_audio_path.wav", "br")
        >>> content = {
        ...     'audio': my_audio_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Audio', 'description')\\
        ...     .with_near_audio(content, encode=True) # <- encode MUST be set to True
        >>> my_audio_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_audio = file_encoder_b64("my_audio_path.wav")
        >>> content = {
        ...     'audio': encoded_audio,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Audio', 'description')\\
        ...     .with_near_audio(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_audio_path.wav", "br") as my_audio_file:
        ...     encoded_audio = file_encoder_b64(my_audio_file)
        >>> content = {
        ...     'audio': encoded_audio,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Audio', 'description')\\
        ...     .with_near_audio(content, encode=False) # <- encode MUST be set to False

        Encode Audio yourself:

        >>> import base64
        >>> with open("my_audio_path.wav", "br") as my_audio_file:
        ...     encoded_audio = base64.b64encode(my_audio_file.read()).decode("utf-8")
        >>> content = {
        ...     'audio': encoded_audio,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Audio', 'description')\\
        ...     .with_near_audio(content, encode=False) # <- encode MUST be set to False

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.AUDIO
        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near_clause = NearAudio(content)
        self._contains_filter = True
        return self

    def with_near_video(self, content: dict, encode: bool = True) -> "GetBuilder":
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

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'video': <str or binary read file>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'video': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance'
        ... }

        With `encoded` True:

        >>> content = {
        ...     'video': "my_video_path.avi",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Video', 'description')\\
        ...     .with_near_video(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_video_file = open("my_video_path.avi", "br")
        >>> content = {
        ...     'video': my_video_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Video', 'description')\\
        ...     .with_near_video(content, encode=True) # <- encode MUST be set to True
        >>> my_video_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_video = file_encoder_b64("my_video_path.avi")
        >>> content = {
        ...     'video': encoded_video,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Video', 'description')\\
        ...     .with_near_video(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64, video_decoder_b64
        >>> with open("my_video_path.avi", "br") as my_video_file:
        ...     encoded_video = file_encoder_b64(my_video_file)
        >>> content = {
        ...     'video': encoded_video,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Video', 'description')\\
        ...     .with_near_video(content, encode=False) # <- encode MUST be set to False

        Encode Video yourself:

        >>> import base64
        >>> with open("my_video_path.avi", "br") as my_video_file:
        ...     encoded_video = base64.b64encode(my_video_file.read()).decode("utf-8")
        >>> content = {
        ...     'video': encoded_video,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Video', 'description')\\
        ...     .with_near_video(content, encode=False) # <- encode MUST be set to False

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.VIDEO
        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near_clause = NearVideo(content)
        self._contains_filter = True
        return self

    def with_near_depth(self, content: dict, encode: bool = True) -> "GetBuilder":
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

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'depth': <str or binary read file>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'depth': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance'
        ... }

        With `encoded` True:

        >>> content = {
        ...     'depth': "my_depth_path.png",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Depth', 'description')\\
        ...     .with_near_depth(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_depth_file = open("my_depth_path.png", "br")
        >>> content = {
        ...     'depth': my_depth_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Depth', 'description')\\
        ...     .with_near_depth(content, encode=True) # <- encode MUST be set to True
        >>> my_depth_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_depth = file_encoder_b64("my_depth_path.png")
        >>> content = {
        ...     'depth': encoded_depth,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Depth', 'description')\\
        ...     .with_near_depth(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_depth_path.png", "br") as my_depth_file:
        ...     encoded_depth = file_encoder_b64(my_depth_file)
        >>> content = {
        ...     'depth': encoded_depth,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Depth', 'description')\\
        ...     .with_near_depth(content, encode=False) # <- encode MUST be set to False

        Encode Depth yourself:

        >>> import base64
        >>> with open("my_depth_path.png", "br") as my_depth_file:
        ...     encoded_depth = base64.b64encode(my_depth_file.read()).decode("utf-8")
        >>> content = {
        ...     'depth': encoded_depth,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Depth', 'description')\\
        ...     .with_near_depth(content, encode=False) # <- encode MUST be set to False

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.DEPTH
        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near_clause = NearDepth(content)
        self._contains_filter = True
        return self

    def with_near_thermal(self, content: dict, encode: bool = True) -> "GetBuilder":
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

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'thermal': <str or binary read file>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'thermal': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance'
        ... }

        With `encoded` True:

        >>> content = {
        ...     'thermal': "my_thermal_path.png",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Thermal', 'description')\\
        ...     .with_near_thermal(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_thermal_file = open("my_thermal_path.png", "br")
        >>> content = {
        ...     'thermal': my_thermal_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Thermal', 'description')\\
        ...     .with_near_thermal(content, encode=True) # <- encode MUST be set to True
        >>> my_thermal_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_thermal = file_encoder_b64("my_thermal_path.png")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Thermal', 'description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = file_encoder_b64(my_thermal_file)
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Thermal', 'description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        Encode Thermal yourself:

        >>> import base64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = base64.b64encode(my_thermal_file.read()).decode("utf-8")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('Thermal', 'description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.THERMAL
        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near_clause = NearThermal(content)
        self._contains_filter = True
        return self

    def with_near_imu(self, content: dict, encode: bool = True) -> "GetBuilder":
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

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'thermal': <str or binary read file>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'thermal': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance'
        ... }

        With `encoded` True:

        >>> content = {
        ...     'thermal': "my_thermal_path.png",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('IMU', 'description')\\
        ...     .with_near_thermal(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_thermal_file = open("my_thermal_path.png", "br")
        >>> content = {
        ...     'thermal': my_thermal_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('IMU', 'description')\\
        ...     .with_near_thermal(content, encode=True) # <- encode MUST be set to True
        >>> my_thermal_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_thermal = file_encoder_b64("my_thermal_path.png")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('IMU', 'description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = file_encoder_b64(my_thermal_file)
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('IMU', 'description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        Encode IMU yourself:

        >>> import base64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = base64.b64encode(my_thermal_file.read()).decode("utf-8")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.get('IMU', 'description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        self._media_type = MediaType.IMU
        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if encode:
            content[self._media_type.value] = file_encoder_b64(content[self._media_type.value])
        self._near_clause = NearIMU(content)
        self._contains_filter = True
        return self

    def with_limit(self, limit: int) -> "GetBuilder":
        """
        The limit of objects returned.

        Parameters
        ----------
        limit : int
            The max number of objects returned.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        ValueError
            If 'limit' is non-positive.
        """

        if limit < 1:
            raise ValueError("limit cannot be non-positive (limit >=1).")

        self._limit = limit
        self._contains_filter = True
        return self

    def with_offset(self, offset: int) -> "GetBuilder":
        """
        The offset of objects returned, i.e. the starting index of the returned objects should be
        used in conjunction with the `with_limit` method.

        Parameters
        ----------
        offset : int
            The offset used for the returned objects.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        ValueError
            If 'offset' is non-positive.
        """

        if offset < 0:
            raise ValueError("offset cannot be non-positive (offset >=0).")

        self._offset = f"offset: {offset} "
        self._contains_filter = True
        return self

    def with_ask(self, content: dict) -> "GetBuilder":
        """
        Ask a question for which weaviate will retrieve the answer from your data.
        This filter can be used only with QnA module: qna-transformers.
        NOTE: The 'autocorrect' field is enabled only with the `text-spellcheck` Weaviate module.

        Parameters
        ----------
        content : dict
            The content of the `ask` filter to set. See examples below.

        Examples
        --------
        Content full prototype:

        >>> content = {
        ...     'question' : <str>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'properties': <list of str or str> # Optional
        ...     'autocorrect': <bool>, # Optional
        ... }

        Full content:

        >>> content = {
        ...     'question' : "What is the NLP?",
        ...     'certainty': 0.7, # or 'distance'
        ...     'properties': ['body'] # search the answer in these properties only.
        ...     'autocorrect': True
        ... }

        Minimal content:

        >>> content = {
        ...     'question' : "What is the NLP?"
        ... }

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.
        """

        if self._near_clause is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_clause = Ask(content)
        self._contains_filter = True
        return self

    def with_additional(
        self,
        properties: Union[
            List, str, Dict[str, Union[List[str], str]], Tuple[dict, dict], AdditionalProperties
        ],
    ) -> "GetBuilder":
        """
        Add additional properties (i.e. properties from `_additional` clause). See Examples below.
        If the the 'properties' is of data type `str` or `list` of `str` then the method is
        idempotent, if it is of type `dict` or `tuple` then the exiting property is going to be
        replaced. To set the setting of one of the additional property use the `tuple` data type
        where `properties` look like this (clause: dict, settings: dict) where the 'settings' are
        the properties inside the '(...)' of the clause. See Examples for more information.

        Parameters
        ----------
        properties : str, list of str, dict[str, str], dict[str, list of str] or tuple[dict, dict]
            The additional properties to include in the query. Can be property name as `str`,
            a list of property names, a dictionary (clause without settings) where the value is a
            `str` or list of `str`, or a `tuple` of 2 elements:
                (clause: Dict[str, str or list[str]], settings: Dict[str, Any])
            where the 'clause' is the property and all its sub-properties and the 'settings' is the
            setting of the property, i.e. everything that is inside the `(...)` right after the
            property name. See Examples below.

        Examples
        --------

        >>> # single additional property with this GraphQL query
        >>> '''
        ... {
        ...     Get {
        ...         Article {
        ...             title
        ...             author
        ...             _additional {
        ...                 id
        ...             }
        ...         }
        ...     }
        ... }
        ... '''
        >>> client.query\\
        ...     .get('Article', ['title', 'author'])\\
        ...     .with_additional('id']) # argument as `str`

        >>> # multiple additional property with this GraphQL query
        >>> '''
        ... {
        ...     Get {
        ...         Article {
        ...             title
        ...             author
        ...             _additional {
        ...                 id
        ...                 certainty
        ...             }
        ...         }
        ...     }
        ... }
        ... '''
        >>> client.query\\
        ...     .get('Article', ['title', 'author'])\\
        ...     .with_additional(['id', 'certainty']) # argument as `List[str]`

        >>> # additional properties as clause with this GraphQL query
        >>> '''
        ... {
        ...     Get {
        ...         Article {
        ...             title
        ...             author
        ...             _additional {
        ...                 classification {
        ...                     basedOn
        ...                     classifiedFields
        ...                     completed
        ...                     id
        ...                     scope
        ...                 }
        ...             }
        ...         }
        ...     }
        ... }
        ... '''
        >>> client.query\\
        ...     .get('Article', ['title', 'author'])\\
        ...     .with_additional(
        ...         {
        ...             'classification' : ['basedOn', 'classifiedFields', 'completed', 'id']
        ...         }
        ...     ) # argument as `dict[str, List[str]]`
        >>> # or with this GraphQL query
        >>> '''
        ... {
        ...     Get {
        ...         Article {
        ...             title
        ...             author
        ...             _additional {
        ...                 classification {
        ...                     completed
        ...                 }
        ...             }
        ...         }
        ...     }
        ... }
        ... '''
        >>> client.query\\
        ...     .get('Article', ['title', 'author'])\\
        ...     .with_additional(
        ...         {
        ...             'classification' : 'completed'
        ...         }
        ...     ) # argument as `Dict[str, str]`

        Consider the following GraphQL clause:

        >>> '''
        ... {
        ...     Get {
        ...         Article {
        ...             title
        ...             author
        ...             _additional {
        ...                 token (
        ...                     properties: ["content"]
        ...                     limit: 10
        ...                     certainty: 0.8
        ...                 ) {
        ...                     certainty
        ...                     endPosition
        ...                     entity
        ...                     property
        ...                     startPosition
        ...                     word
        ...                 }
        ...             }
        ...         }
        ...     }
        ... }
        ... '''

        Then the python translation of this is the following:

        >>> clause = {
        ...     'token': [ # if only one, can be passes as `str`
        ...         'certainty',
        ...         'endPosition',
        ...         'entity',
        ...         'property',
        ...         'startPosition',
        ...         'word',
        ...     ]
        ... }
        >>> settings = {
        ...     'properties': ["content"],  # is required
        ...     'limit': 10,                # optional, int
        ...     'certainty': 0.8            # optional, float
        ... }
        >>> client.query\\
        ...     .get('Article', ['title', 'author'])\\
        ...     .with_additional(
        ...         (clause, settings)
        ...     ) # argument as `Tuple[Dict[str, List[str]], Dict[str, Any]]`

        If the desired clause does not match any example above, then the clause can always be
        converted to string before passing it to the `.with_additional()` method.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.

        Raises
        ------
        TypeError
            If one of the property is not of a correct data type.
        """
        if isinstance(properties, AdditionalProperties):
            if len(self._additional) > 1 or len(self._additional["__one_level"]) > 0:
                raise AdditionalPropertiesException(
                    str(self._additional), str(self._additional_dataclass)
                )
            self._additional_dataclass = properties
            return self
        elif self._additional_dataclass is not None:
            raise AdditionalPropertiesException(
                str(self._additional), str(self._additional_dataclass)
            )

        if isinstance(properties, str):
            self._additional["__one_level"].add(properties)
            return self

        if isinstance(properties, list):
            for prop in properties:
                if not isinstance(prop, str):
                    raise TypeError(
                        "If type of 'properties' is `list` then all items must be of type `str`!"
                    )
                self._additional["__one_level"].add(prop)
            return self

        if isinstance(properties, tuple):
            self._tuple_to_dict(properties)
            return self

        if not isinstance(properties, dict):
            raise TypeError(
                "The 'properties' argument must be either of type `str`, `list`, `dict` or "
                f"`tuple`! Given: {type(properties)}"
            )

        # only `dict` type here
        for key, values in properties.items():
            if not isinstance(key, str):
                raise TypeError(
                    "If type of 'properties' is `dict` then all keys must be of type `str`!"
                )
            self._additional[key] = set()
            if isinstance(values, str):
                self._additional[key].add(values)
                continue
            if not isinstance(values, list):
                raise TypeError(
                    "If type of 'properties' is `dict` then all the values must be either of type "
                    f"`str` or `list` of `str`! Given: {type(values)}!"
                )
            if len(values) == 0:
                raise ValueError(
                    "If type of 'properties' is `dict` and a value is of type `list` then at least"
                    " one element should be present!"
                )
            for value in values:
                if not isinstance(value, str):
                    raise TypeError(
                        "If type of 'properties' is `dict` and a value is of type `list` then all "
                        "items must be of type `str`!"
                    )
                self._additional[key].add(value)
        return self

    def with_sort(self, content: Union[list, dict]) -> "GetBuilder":
        """
        Sort objects based on specific field/s. Multiple sort fields can be used, the objects are
        going to be sorted according to order of the sort configs passed. This method can be called
        multiple times and it does not overwrite the last entry but appends it to the previous
        ones, see examples below.

        Parameters
        ----------
        content : Union[list, dict]
            The content of the Sort filter. Can be a single Sort configuration or a list of
            configurations.

        Examples
        --------
        The `content` should have this form:

        >>> content = {
        ...     'path': ['name']       # Path to the property that should be used
        ...     'order': 'asc'         # Sort order, possible values: asc, desc
        ... }
        >>> client.query.get('Author', ['name', 'address'])\\
        ...     .with_sort(content)

        Or a list of sort configurations:

        >>> content = [
        ...     {
        ...         'path': ['name']        # Path to the property that should be used
        ...         'order': 'asc'          # Sort order, possible values: asc, desc
        ...     },
        ...         'path': ['address']     # Path to the property that should be used
        ...         'order': 'desc'         # Sort order, possible values: asc, desc
        ...     }
        ... ]

        If we have a list we can add it in 2 ways.
        Pass the list:

        >>> client.query.get('Author', ['name', 'address'])\\
        ...     .with_sort(content)

        Or one configuration at a time:

        >>> client.query.get('Author', ['name', 'address'])\\
        ...     .with_sort(content[0])
        ...     .with_sort(content[1])

        It is possible to call this method multiple times with lists only too.


        Returns
        -------
        weaviate.gql.get.GetBuilder
            The updated GetBuilder.
        """

        if self._sort is None:
            self._sort = Sort(content=content)
            self._contains_filter = True
        else:
            self._sort.add(content=content)
        return self

    def with_bm25(self, query: str, properties: Optional[List[str]] = None) -> "GetBuilder":
        """Add BM25 query to search the inverted index for keywords.

        Parameters
        ----------
        query: str
            The query to search for.
        properties: Optional[List[str]]
            Which properties should be searched. If 'None' or empty all properties will be searched. By default, None
        """
        self._bm25 = BM25(query, properties)
        self._contains_filter = True

        return self

    def with_hybrid(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
    ) -> "GetBuilder":
        """Get objects using bm25 and vector, then combine the results using a reciprocal ranking algorithm.

        Parameters
        ----------
        query: str
            The query to search for.
        alpha: Optional[float]
            Factor determining how BM25 and vector search are weighted. If 'None' the weaviate default of 0.75 is used.
            By default, None
            alpha = 0 -> bm25, alpha=1 -> vector search
        vector: Optional[List[float]]
            Vector that is searched for. If 'None', weaviate will use the configured text-to-vector module to create a
            vector from the "query" field.
            By default, None
        properties: Optional[List[str]]:
            Which properties should be searched by BM25. Does not have any effect for vector search. If None or empty
            all properties are searched.
        fusion_type: Optional[HybridFusionType]:
            Which fusion type should be used to merge keyword and vector search.
        """
        self._hybrid = Hybrid(query, alpha, vector, properties, fusion_type)
        self._contains_filter = True
        return self

    def with_group_by(
        self, properties: List[str], groups: int, objects_per_group: int
    ) -> "GetBuilder":
        """Retrieve groups of objects from Weaviate.

        Note that the return values must be set using .with_additional() to see the output.

        Parameters
        ----------
        properties: List[str]
            Properties to group by
        groups: int
            Maximum number of groups
        objects_per_group: int
            Maximum number of objects per group

        """
        self._group_by = GroupBy(properties, groups, objects_per_group)
        self._contains_filter = True
        return self

    def with_generate(
        self,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
    ) -> "GetBuilder":
        """Generate responses using the OpenAI generative search.

        At least one of the two parameters must be set.

        Parameters
        ----------
        grouped_task: Optional[str]
            The task to generate a grouped response.
        grouped_properties: Optional[List[str]]:
            The properties whose contents are added to the prompts. If None or empty,
            all text properties contents are added.
        single_prompt: Optional[str]
            The prompt to generate a single response.
        """
        if single_prompt is None and grouped_task is None:
            raise TypeError(
                "Either parameter grouped_result_task or single_result_prompt must be not None."
            )
        if (single_prompt is not None and not isinstance(single_prompt, str)) or (
            grouped_task is not None and not isinstance(grouped_task, str)
        ):
            raise TypeError("prompts and tasks must be of type str.")

        if self._connection.server_version < "1.17.3":
            _Warnings.weaviate_too_old_for_openai(self._connection.server_version)

        results: List[str] = ["error"]
        task_and_prompt = ""
        if single_prompt is not None:
            results.append("singleResult")
            task_and_prompt += f"singleResult:{{prompt:{util._sanitize_str(single_prompt)}}}"
        if grouped_task is not None or (
            grouped_properties is not None and len(grouped_properties) > 0
        ):
            results.append("groupedResult")
            args = []
            if grouped_task is not None:
                args.append(f"task:{util._sanitize_str(grouped_task)}")
            if grouped_properties is not None and len(grouped_properties) > 0:
                props = '","'.join(grouped_properties)
                args.append(f'properties:["{props}"]')
            task_and_prompt += f'groupedResult:{{{",".join(args)}}}'

        self._additional["__one_level"].add(f'generate({task_and_prompt}){{{" ".join(results)}}}')

        return self

    def with_alias(
        self,
        alias: str,
    ) -> "GetBuilder":
        """Gives an alias for the query. Needs to be used if 'multi_get' requests the same 'class_name' twice.

        Parameters
        ----------
        alias: str
            The alias for the query.
        """

        self._alias = alias
        return self

    def with_consistency_level(self, consistency_level: ConsistencyLevel) -> "GetBuilder":
        """Set the consistency level for the request."""

        self._consistency_level = f"consistencyLevel: {consistency_level.value} "
        self._contains_filter = True
        return self

    def build(self, wrap_get: bool = True) -> str:
        """
        Build query filter as a string.

        Parameters
        ----------
        wrap_get: bool
            A boolean to decide wether {Get{...}} is placed around the query. Useful for multi_get.

        Returns
        -------
        str
            The GraphQL query as a string.
        """
        if wrap_get:
            query = "{Get{"
        else:
            query = ""

        if self._alias is not None:
            query += self._alias + ": "
        query += self._class_name
        if self._contains_filter:
            query += "("
            if self._where is not None:
                query += str(self._where)
            if self._limit is not None:
                query += f"limit: {self._limit} "
            if self._offset is not None:
                query += self._offset
            if self._near_clause is not None:
                query += str(self._near_clause)
            if self._sort is not None:
                query += str(self._sort)
            if self._bm25 is not None:
                query += str(self._bm25)
            if self._hybrid is not None:
                query += str(self._hybrid)
            if self._group_by is not None:
                query += str(self._group_by)
            if self._after is not None:
                query += self._after
            if self._consistency_level is not None:
                query += self._consistency_level
            if self._tenant is not None:
                query += f'tenant: "{self._tenant}"'
            if self._autocut is not None:
                query += f"autocut: {self._autocut}"

            query += ")"

        additional_props = self._additional_to_str()

        if not (additional_props or self._properties):
            raise AttributeError(
                "No 'properties' or 'additional properties' specified to be returned. "
                "At least one should be included."
            )

        properties = " ".join(str(x) for x in self._properties) + self._additional_to_str()
        query += "{" + properties + "}"
        if wrap_get:
            query += "}}"
        return query

    def do(self) -> dict:
        """
        Builds and runs the query.

        Returns
        -------
        dict
            The response of the query.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """
        grpc_enabled = (  # only implemented for some scenarios
            self._connection.grpc_stub is not None
            and (
                self._near_clause is None
                or isinstance(self._near_clause, NearVector)
                or isinstance(self._near_clause, NearObject)
            )
            and len(self._additional) == 1
            and (
                len(self._additional["__one_level"]) == 0 or "id" in self._additional["__one_level"]
            )
            and self._offset is None
            and self._sort is None
            and self._where is None
            and self._after is None
            and all(
                "..." not in prop and "_additional" not in prop
                for prop in self._properties
                if isinstance(prop, str)
            )  # no ref props as strings
        )
        if grpc_enabled:
            metadata: Union[Tuple, Tuple[Tuple[Literal["authorization"], str]]] = ()
            access_token = self._connection.get_current_bearer_token()
            if len(access_token) > 0:
                metadata = (("authorization", access_token),)

            try:
                res, _ = self._connection.grpc_stub.Search.with_call(  # type: ignore
                    weaviate_pb2.SearchRequest(
                        class_name=self._class_name,
                        limit=self._limit,
                        near_vector=weaviate_pb2.NearVectorParams(
                            vector=self._near_clause.content["vector"],
                            certainty=self._near_clause.content.get("certainty", None),
                            distance=self._near_clause.content.get("distance", None),
                        )
                        if self._near_clause is not None
                        and isinstance(self._near_clause, NearVector)
                        else None,
                        near_object=weaviate_pb2.NearObjectParams(
                            id=self._near_clause.content["id"],
                            certainty=self._near_clause.content.get("certainty", None),
                            distance=self._near_clause.content.get("distance", None),
                        )
                        if self._near_clause is not None
                        and isinstance(self._near_clause, NearObject)
                        else None,
                        properties=self._convert_references_to_grpc(self._properties),
                        additional_properties=weaviate_pb2.AdditionalProperties(
                            uuid=self._additional_dataclass.uuid,
                            vector=self._additional_dataclass.vector,
                            creationTimeUnix=self._additional_dataclass.creationTimeUnix,
                            lastUpdateTimeUnix=self._additional_dataclass.lastUpdateTimeUnix,
                            distance=self._additional_dataclass.distance,
                            explainScore=self._additional_dataclass.explainScore,
                            score=self._additional_dataclass.score,
                        )
                        if self._additional_dataclass is not None
                        else None,
                        bm25_search=weaviate_pb2.BM25SearchParams(
                            properties=self._bm25.properties, query=self._bm25.query
                        )
                        if self._bm25 is not None
                        else None,
                        hybrid_search=weaviate_pb2.HybridSearchParams(
                            properties=self._hybrid.properties,
                            query=self._hybrid.query,
                            alpha=self._hybrid.alpha,
                            vector=self._hybrid.vector,
                        )
                        if self._hybrid is not None
                        else None,
                    ),
                    metadata=metadata,
                )

                objects = []
                for result in res.results:
                    obj = self._convert_references_to_grpc_result(result.properties)
                    additional = self._extract_additional_properties(result.additional_properties)
                    if len(additional) > 0:
                        obj["_additional"] = additional
                    objects.append(obj)

                results: Union[Dict[str, Dict[str, Dict[str, List]]], Dict[str, List]] = {
                    "data": {"Get": {self._class_name: objects}}
                }

            except grpc.RpcError as e:
                results = {"errors": [e.details()]}
            return results
        else:
            return super().do()

    def _extract_additional_properties(
        self, props: "weaviate_pb2.ResultAdditionalProps"
    ) -> Dict[str, str]:
        additional_props: Dict[str, Any] = {}
        if self._additional_dataclass is None:
            return additional_props

        if self._additional_dataclass.uuid:
            additional_props["id"] = props.id
        if self._additional_dataclass.vector:
            additional_props["vector"] = (
                [float(num) for num in props.vector] if len(props.vector) > 0 else None
            )
        if self._additional_dataclass.distance:
            additional_props["distance"] = props.distance if props.distance_present else None
        if self._additional_dataclass.certainty:
            additional_props["certainty"] = props.certainty if props.certainty_present else None
        if self._additional_dataclass.creationTimeUnix:
            additional_props["creationTimeUnix"] = (
                str(props.creation_time_unix) if props.creation_time_unix_present else None
            )
        if self._additional_dataclass.lastUpdateTimeUnix:
            additional_props["lastUpdateTimeUnix"] = (
                str(props.last_update_time_unix) if props.last_update_time_unix_present else None
            )
        if self._additional_dataclass.score:
            additional_props["score"] = props.score if props.score_present else None
        if self._additional_dataclass.explainScore:
            additional_props["explainScore"] = (
                props.explain_score if props.explain_score_present else None
            )
        return additional_props

    def _convert_references_to_grpc_result(
        self, properties: "weaviate_pb2.ResultProperties"
    ) -> Dict:
        result: Dict[str, Any] = {}
        for name, non_ref_prop in properties.non_ref_properties.items():
            result[name] = non_ref_prop

        for ref_prop in properties.ref_props:
            result[ref_prop.prop_name] = [
                self._convert_references_to_grpc_result(prop) for prop in ref_prop.properties
            ]

        return result

    def _convert_references_to_grpc(
        self, properties: List[Union[LinkTo, str]]
    ) -> "weaviate_pb2.Properties":
        return weaviate_pb2.Properties(
            non_ref_properties=[prop for prop in properties if isinstance(prop, str)],
            ref_properties=[
                weaviate_pb2.RefProperties(
                    linked_class=prop.linked_class,
                    reference_property=prop.link_on,
                    linked_properties=self._convert_references_to_grpc(prop.properties),
                )
                for prop in properties
                if isinstance(prop, LinkTo)
            ],
        )

    def _additional_to_str(self) -> str:
        """
        Convert `self._additional` attribute to a `str`.

        Returns
        -------
        str
            The converted self._additional.
        """
        if self._additional_dataclass is not None:
            return str(self._additional_dataclass)

        str_to_return = " _additional {"

        has_values = False
        for one_level in sorted(self._additional["__one_level"]):
            has_values = True
            str_to_return += one_level + " "

        for key, values in sorted(self._additional.items(), key=lambda key_value: key_value[0]):
            if key == "__one_level":
                continue
            has_values = True
            str_to_return += key + " {"
            for value in sorted(values):
                str_to_return += value + " "
            str_to_return += "} "

        if has_values is False:
            return ""
        return str_to_return + "}"

    def _tuple_to_dict(self, tuple_value: tuple) -> None:
        """
        Convert the tuple data type argument to a dictionary.

        Parameters
        ----------
        tuple_value : tuple
            The tuple value as (clause: <dict>, settings: <dict>).

        Raises
        ------
        ValueError
            If 'tuple_value' does not have exactly 2 elements.
        TypeError
            If the configuration of the 'tuple_value' is not correct.
        """

        if len(tuple_value) != 2:
            raise ValueError(
                "If type of 'properties' is `tuple` then it should have length 2: "
                "(clause: <dict>, settings: <dict>)"
            )

        clause, settings = tuple_value
        if not isinstance(clause, dict) or not isinstance(settings, dict):
            raise TypeError(
                "If type of 'properties' is `tuple` then it should have this data type: "
                "(<dict>, <dict>)"
            )
        if len(clause) != 1:
            raise ValueError(
                "If type of 'properties' is `tuple` then the 'clause' (first element) should "
                f"have only one key. Given: {len(clause)}"
            )
        if len(settings) == 0:
            raise ValueError(
                "If type of 'properties' is `tuple` then the 'settings' (second element) should "
                f"have at least one key. Given: {len(settings)}"
            )

        clause_key, values = list(clause.items())[0]

        if not isinstance(clause_key, str):
            raise TypeError(
                "If type of 'properties' is `tuple` then first element's key should be of type "
                "`str`!"
            )

        clause_with_settings = clause_key + "("
        try:
            for key, value in sorted(settings.items(), key=lambda key_value: key_value[0]):
                if not isinstance(key, str):
                    raise TypeError(
                        "If type of 'properties' is `tuple` then the second elements (<dict>) "
                        "should have all the keys of type `str`!"
                    )
                clause_with_settings += key + ": " + dumps(value) + " "
        except TypeError:
            raise TypeError(
                "If type of 'properties' is `tuple` then the second elements (<dict>) "
                "should have all the keys of type `str`!"
            ) from None
        clause_with_settings += ")"

        self._additional[clause_with_settings] = set()
        if isinstance(values, str):
            self._additional[clause_with_settings].add(values)
            return
        if not isinstance(values, list):
            raise TypeError(
                "If type of 'properties' is `tuple` then first element's dict values must be "
                f"either of type `str` or `list` of `str`! Given: {type(values)}!"
            )
        if len(values) == 0:
            raise ValueError(
                "If type of 'properties' is `tuple` and first element's dict value is of type "
                "`list` then at least one element should be present!"
            )
        for value in values:
            if not isinstance(value, str):
                raise TypeError(
                    "If type of 'properties' is `tuple` and first element's dict value is of type "
                    " `list` then all items must be of type `str`!"
                )
            self._additional[clause_with_settings].add(value)
