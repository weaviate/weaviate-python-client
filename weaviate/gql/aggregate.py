"""
GraphQL `Aggregate` command.
"""

import json
from typing import List, Optional, Union

from weaviate.connect import Connection, ConnectionV4
from weaviate.util import (
    _capitalize_first_letter,
    file_encoder_b64,
)
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


class AggregateBuilder(GraphQL):
    """
    AggregateBuilder class used to aggregate Weaviate objects.
    """

    def __init__(self, class_name: str, connection: Union[Connection, ConnectionV4]):
        """
        Initialize a AggregateBuilder class instance.

        Parameters
        ----------
        class_name : str
            Class name of the objects to be aggregated.
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        """

        super().__init__(connection)
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
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._where = Where(content)
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
        ...     'certainty': 0.7, # or 'distance' instead
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
        ...     'certainty': 0.7, # or 'distance' instead
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
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
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
        ...     'certainty': 0.75, # or 'distance' instead
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
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
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

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'id': <str>, # OR 'beacon'
        ...     'beacon': <str>, # OR 'id'
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'id': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> # alternatively
        >>> {
        ...     'beacon': "weaviate://localhost/Book/e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf"
        ...     'certainty': 0.7 # or 'distance' instead
        ... }

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        is_server_version_14 = self._connection.server_version >= "1.14"

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
        self._near = NearObject(content, is_server_version_14)
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
        >>> query = client.query.aggregate('Image')\\
                .with_fields('description')\\
        ...     .with_near_image(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_image_file = open("my_image_path.png", "br")
        >>> content = {
        ...     'image': my_image_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Image')\\
                .with_fields('description')\\
        ...     .with_near_image(content, encode=True) # <- encode MUST be set to True
        >>> my_image_file.close()

        With `encoded` False:

        >>> from weaviate.util import image_encoder_b64, image_decoder_b64
        >>> encoded_image = image_encoder_b64("my_image_path.png")
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Image')\\
                .with_fields('description')\\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import image_encoder_b64, image_decoder_b64
        >>> with open("my_image_path.png", "br") as my_image_file:
        ...     encoded_image = image_encoder_b64(my_image_file)
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Image')\\
                .with_fields('description')\\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

        Encode Image yourself:

        >>> import base64
        >>> with open("my_image_path.png", "br") as my_image_file:
        ...     encoded_image = base64.b64encode(my_image_file.read()).decode("utf-8")
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Image')\\
                .with_fields('description')\\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

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
        >>> query = client.query.aggregate('Audio')\\
                .with_fields('description')\\
        ...     .with_near_audio(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_audio_file = open("my_audio_path.wav", "br")
        >>> content = {
        ...     'audio': my_audio_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Audio')\\
                .with_fields('description')\\
        ...     .with_near_audio(content, encode=True) # <- encode MUST be set to True
        >>> my_audio_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_audio = file_encoder_b64("my_audio_path.wav")
        >>> content = {
        ...     'audio': encoded_audio,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Audio')\\
                .with_fields('description')\\
        ...     .with_near_audio(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_audio_path.wav", "br") as my_audio_file:
        ...     encoded_audio = file_encoder_b64(my_audio_file)
        >>> content = {
        ...     'audio': encoded_audio,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Audio')\\
                .with_fields('description')\\
        ...     .with_near_audio(content, encode=False) # <- encode MUST be set to False

        Encode Audio yourself:

        >>> import base64
        >>> with open("my_audio_path.wav", "br") as my_audio_file:
        ...     encoded_audio = base64.b64encode(my_audio_file.read()).decode("utf-8")
        >>> content = {
        ...     'audio': encoded_audio,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Audio')\\
                .with_fields('description')\\
        ...     .with_near_audio(content, encode=False) # <- encode MUST be set to False

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
        >>> query = client.query.aggregate('Video')\\
                .with_fields('description')\\
        ...     .with_near_video(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_video_file = open("my_video_path.avi", "br")
        >>> content = {
        ...     'video': my_video_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Video')\\
                .with_fields('description')\\
        ...     .with_near_video(content, encode=True) # <- encode MUST be set to True
        >>> my_video_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_video = file_encoder_b64("my_video_path.avi")
        >>> content = {
        ...     'video': encoded_video,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Video')\\
                .with_fields('description')\\
        ...     .with_near_video(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64, video_decoder_b64
        >>> with open("my_video_path.avi", "br") as my_video_file:
        ...     encoded_video = file_encoder_b64(my_video_file)
        >>> content = {
        ...     'video': encoded_video,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Video')\\
                .with_fields('description')\\
        ...     .with_near_video(content, encode=False) # <- encode MUST be set to False

        Encode Video yourself:

        >>> import base64
        >>> with open("my_video_path.avi", "br") as my_video_file:
        ...     encoded_video = base64.b64encode(my_video_file.read()).decode("utf-8")
        >>> content = {
        ...     'video': encoded_video,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Video')\\
                .with_fields('description')\\
        ...     .with_near_video(content, encode=False) # <- encode MUST be set to False

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
        >>> query = client.query.aggregate('Depth')\\
                .with_fields('description')\\
        ...     .with_near_depth(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_depth_file = open("my_depth_path.png", "br")
        >>> content = {
        ...     'depth': my_depth_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Depth')\\
                .with_fields('description')\\
        ...     .with_near_depth(content, encode=True) # <- encode MUST be set to True
        >>> my_depth_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_depth = file_encoder_b64("my_depth_path.png")
        >>> content = {
        ...     'depth': encoded_depth,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Depth')\\
                .with_fields('description')\\
        ...     .with_near_depth(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_depth_path.png", "br") as my_depth_file:
        ...     encoded_depth = file_encoder_b64(my_depth_file)
        >>> content = {
        ...     'depth': encoded_depth,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Depth')\\
                .with_fields('description')\\
        ...     .with_near_depth(content, encode=False) # <- encode MUST be set to False

        Encode Depth yourself:

        >>> import base64
        >>> with open("my_depth_path.png", "br") as my_depth_file:
        ...     encoded_depth = base64.b64encode(my_depth_file.read()).decode("utf-8")
        >>> content = {
        ...     'depth': encoded_depth,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Depth')\\
                .with_fields('description')\\
        ...     .with_near_depth(content, encode=False) # <- encode MUST be set to False

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
        >>> query = client.query.aggregate('Thermal')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=True) # <- encode MUST be set to True
        >>> my_thermal_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_thermal = file_encoder_b64("my_thermal_path.png")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Thermal')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = file_encoder_b64(my_thermal_file)
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Thermal')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        Encode Thermal yourself:

        >>> import base64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = base64.b64encode(my_thermal_file.read()).decode("utf-8")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('Thermal')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

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
        >>> query = client.query.aggregate('IMU')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_thermal_file = open("my_thermal_path.png", "br")
        >>> content = {
        ...     'thermal': my_thermal_file,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('IMU')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=True) # <- encode MUST be set to True
        >>> my_thermal_file.close()

        With `encoded` False:

        >>> from weaviate.util import file_encoder_b64
        >>> encoded_thermal = file_encoder_b64("my_thermal_path.png")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('IMU')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import file_encoder_b64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = file_encoder_b64(my_thermal_file)
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('IMU')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

        Encode IMU yourself:

        >>> import base64
        >>> with open("my_thermal_path.png", "br") as my_thermal_file:
        ...     encoded_thermal = base64.b64encode(my_thermal_file.read()).decode("utf-8")
        >>> content = {
        ...     'thermal': encoded_thermal,
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> query = client.query.aggregate('IMU')\\
        ...     .with_fields('description')\\
        ...     .with_near_thermal(content, encode=False) # <- encode MUST be set to False

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
