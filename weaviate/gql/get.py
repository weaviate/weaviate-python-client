"""
GraphQL `Get` command.
"""
from dataclasses import dataclass
from json import dumps
from typing import List, Union, Optional, Dict, Tuple

from weaviate.connect import Connection
from weaviate.gql.filter import (
    Where,
    NearText,
    NearVector,
    GraphQL,
    NearObject,
    Filter,
    Ask,
    NearImage,
    Sort,
)
from weaviate.types import UUID
from weaviate.util import image_encoder_b64, _capitalize_first_letter, get_valid_uuid
from weaviate.warnings import _Warnings


@dataclass
class BM25:
    query: str
    properties: Optional[List[str]]

    def __str__(self) -> str:
        ret = f'query: "{self.query}"'
        if self.properties is not None and len(self.properties) > 0:
            props = '","'.join(self.properties)
            ret += f', properties: ["{props}"]'
        return "bm25:{" + ret + "}"


@dataclass
class Hybrid:
    query: str
    alpha: float
    vector: List[float]

    def __str__(self) -> str:
        ret = f'query: "{self.query}"'
        if self.vector is not None:
            ret += f", vector: {self.vector}"
        if self.alpha is not None:
            ret += f", alpha: {self.alpha}"

        return "hybrid:{" + ret + "}"


class GetBuilder(GraphQL):
    """
    GetBuilder class used to create GraphQL queries.
    """

    def __init__(
        self, class_name: str, properties: Union[List[str], str, None], connection: Connection
    ):
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
        for prop in properties:
            if not isinstance(prop, str):
                raise TypeError("All the `properties` must be of type `str`!")

        self._class_name: str = _capitalize_first_letter(class_name)
        self._properties: List[str] = properties
        self._additional: dict = {"__one_level": set()}
        # '__one_level' refers to the additional properties that are just a single word, not a dict
        # thus '__one_level', only one level of complexity
        self._where: Optional[Where] = None  # To store the where filter if it is added
        self._limit: Optional[str] = None  # To store the limit filter if it is added
        self._offset: Optional[str] = None  # To store the offset filter if it is added
        self._after: Optional[str] = None  # To store the offset filter if it is added
        self._near_ask: Optional[Filter] = None  # To store the `near`/`ask` clause if it is added
        self._contains_filter = False  # true if any filter is added
        self._sort: Optional[Sort] = None
        self._bm25: Optional[BM25] = None
        self._hybrid: Optional[Hybrid] = None

    def with_after(self, after_uuid: UUID):
        """Can be used to extract all elements by giving the last ID from the previous "page".

        Requires limit to be set but cannot be combined with any other filters or search. Part of the Cursor API."""
        if not isinstance(after_uuid, UUID.__args__):  # __args__ is workaround for python 3.8
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

        if self._near_ask is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_ask = NearText(content)
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

        if self._near_ask is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_ask = NearVector(content)
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

        if self._near_ask is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_ask = NearObject(content, is_server_version_14)
        self._contains_filter = True
        return self

    def with_near_image(self, content: dict, encode: bool = True) -> "GetBuilder":
        """
        Set `nearImage` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearObject` filter to set. See examples below.
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

        if self._near_ask is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        if encode:
            content["image"] = image_encoder_b64(content["image"])
        self._near_ask = NearImage(content)
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

        self._limit = f"limit: {limit} "
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

        if self._near_ask is not None:
            raise AttributeError(
                "Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!"
            )
        self._near_ask = Ask(content)
        self._contains_filter = True
        return self

    def with_additional(
        self, properties: Union[List, str, Dict[str, Union[List[str], str]], Tuple[dict, dict]]
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
        self, query: str, alpha: Optional[float] = None, vector: Optional[List[float]] = None
    ):
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
        """
        self._hybrid = Hybrid(query, alpha, vector)
        self._contains_filter = True
        return self

    def with_generate(
        self, single_prompt: Optional[str] = None, grouped_task: Optional[str] = None
    ) -> "GetBuilder":
        """Generate responses using the OpenAI generative search.

        At least one of the two parameters must be set.

        Parameters
        ----------
        grouped_task: Optional[str]
            The task to generate a grouped response. One
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
            task_and_prompt += f'singleResult:{{prompt:"{single_prompt}"}}'
        if grouped_task is not None:
            results.append("groupedResult")
            task_and_prompt += f'groupedResult:{{task:"{grouped_task}"}}'

        self._additional["__one_level"].add(f'generate({task_and_prompt}){{{" ".join(results)}}}')

        return self

    def build(self) -> str:
        """
        Build query filter as a string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """

        query = "{Get{" + self._class_name
        if self._contains_filter:
            query += "("
            if self._where is not None:
                query += str(self._where)
            if self._limit is not None:
                query += self._limit
            if self._offset is not None:
                query += self._offset
            if self._near_ask is not None:
                query += str(self._near_ask)
            if self._sort is not None:
                query += str(self._sort)
            if self._bm25 is not None:
                query += str(self._bm25)
            if self._hybrid is not None:
                query += str(self._hybrid)
            if self._after is not None:
                query += self._after

            query += ")"

        additional_props = self._additional_to_str()

        if not (additional_props or self._properties):
            raise AttributeError(
                "No 'properties' or 'additional properties' specified to be returned. "
                "At least one should be included."
            )

        properties = " ".join(self._properties) + self._additional_to_str()
        query += "{" + properties + "}"
        return query + "}}"

    def _additional_to_str(self) -> str:
        """
        Convert `self._additional` attribute to a `str`.

        Returns
        -------
        str
            The converted self._additional.
        """

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
