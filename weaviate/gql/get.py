"""
GraphQL `Get` command.
"""
from json import dumps
from typing import List, Union, Optional, Dict, Tuple
from weaviate.gql.filter import (
    Where,
    NearText,
    NearVector,
    GraphQL,
    NearObject,
    Filter,
    Ask,
    NearImage
)
from weaviate.connect import Connection
from weaviate.util import image_encoder_b64, _capitalize_first_letter


class GetBuilder(GraphQL):
    """
    GetBuilder class used to create GraphQL queries.
    """

    def __init__(self,
            class_name: str,
            properties: Union[List[str], str],
            connection: Connection
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
        if not isinstance(properties, (list, str)):
            raise TypeError("properties must be of type str or "
                f"list of str but was {type(properties)}")
        if isinstance(properties, str):
            properties = [properties]
        for prop in properties:
            if not isinstance(prop, str):
                raise TypeError(
                    "All the `properties` must be of type `str`!"
                )

        self._class_name: str = _capitalize_first_letter(class_name)
        self._properties: List[str] = properties
        self._additional: dict = {'__one_level': set()}
        # '__one_level' refers to the additional properties that are just a single word, not a dict
        # thus '__one_level', only one level of complexity
        self._where: Optional[Where] = None  # To store the where filter if it is added
        self._limit: Optional[str] = None  # To store the limit filter if it is added
        self._offset: Optional[str] = None  # To store the offset filter if it is added
        self._near_ask: Optional[Filter] = None # To store the `near`/`ask` clause if it is added
        self._contains_filter = False  # true if any filter is added

    def with_where(self, content: dict) -> 'GetBuilder':
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

    def with_near_text(self, content: dict) -> 'GetBuilder':
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
        ...     'certainty': <float>, # Optional
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
        ...     'certainty': 0.7,
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
        ...     'certainty': 0.7,
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
            raise AttributeError("Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!")
        self._near_ask = NearText(content)
        self._contains_filter = True
        return self

    def with_near_vector(self, content: dict) -> 'GetBuilder':
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
        ...     'certainty': <float> # Optional
        ... }

        NOTE: Supported types for 'vector' are `list`, 'numpy.ndarray`, `torch.Tensor`
                and `tf.Tensor`.

        Full content:

        >>> content = {
        ...     'vector' : [.1, .2, .3, .5],
        ...     'certainty': 0.75
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
            raise AttributeError("Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!")
        self._near_ask = NearVector(content)
        self._contains_filter = True
        return self

    def with_near_object(self, content: dict) -> 'GetBuilder':
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
        ...     'certainty': 0.7 # Optional
        ... }
        >>> # alternatively
        >>> {
        ...     'beacon': "weaviate://localhost/e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf"
        ...     'certainty': 0.7 # Optional
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
            raise AttributeError("Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!")
        self._near_ask = NearObject(content)
        self._contains_filter = True
        return self

    def with_near_image(self, content: dict, encode: bool = True) -> 'GetBuilder':
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

        >>> {
        ...     'image': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # Optional
        ... }

        With `encoded` True:

        >>> content = {
        ...     'image': "my_image_path.png",
        ...     'certainty': 0.7 # Optional
        ... }
        >>> query = client.query.get('Image', 'description')\
        ...     .with_near_image(content, encode=True) # <- encode MUST be set to True

        OR

        >>> my_image_file = open("my_image_path.png", "br")
        >>> content = {
        ...     'image': my_image_file,
        ...     'certainty': 0.7 # Optional
        ... }
        >>> query = client.query.get('Image', 'description')\
        ...     .with_near_image(content, encode=True) # <- encode MUST be set to True
        >>> my_image_file.close()

        With `encoded` False:

        >>> from weaviate.util import image_encoder_b64, image_decoder_b64
        >>> encoded_image = image_encoder_b64("my_image_path.png")
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # Optional
        ... }
        >>> query = client.query.get('Image', 'description')\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

        OR

        >>> from weaviate.util import image_encoder_b64, image_decoder_b64
        >>> with open("my_image_path.png", "br") as my_image_file:
        ...     encoded_image = image_encoder_b64(my_image_file)
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # Optional
        ... }
        >>> query = client.query.get('Image', 'description')\
        ...     .with_near_image(content, encode=False) # <- encode MUST be set to False

        Encode Image yourself:

        >>> import base64
        >>> with open("my_image_path.png", "br") as my_image_file:
        ...     encoded_image = base64.b64encode(my_image_file.read()).decode("utf-8")
        >>> content = {
        ...     'image': encoded_image,
        ...     'certainty': 0.7 # Optional
        ... }
        >>> query = client.query.get('Image', 'description')\
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
            raise AttributeError("Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!")
        if encode:
            content['image'] = image_encoder_b64(content['image'])
        self._near_ask = NearImage(content)
        self._contains_filter = True
        return self

    def with_limit(self, limit: int) -> 'GetBuilder':
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
            raise ValueError('limit cannot be non-positive (limit >=1).')

        self._limit = f'limit: {limit} '
        self._contains_filter = True
        return self

    def with_offset(self, offset: int) -> 'GetBuilder':
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

        if offset < 1:
            raise ValueError('offset cannot be non-positive (offset >=1).')

        self._offset = f'offset: {offset} '
        self._contains_filter = True
        return self

    def with_ask(self, content: dict) -> 'GetBuilder':
        """
        Ask a question for which weaviate will retreive the answer from your data.
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
        ...     'certainty': <float>, # Optional
        ...     'properties': <list of str or str> # Optional
        ...     'autocorrect': <bool>, # Optional
        ... }

        Full content:

        >>> content = {
        ...     'question' : "What is the NLP?",
        ...     'certainty': 0.7,
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
            raise AttributeError("Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!")
        self._near_ask = Ask(content)
        self._contains_filter = True
        return self

    def with_additional(self,
            properties: Union[List, str, Dict[str, Union[List[str], str]],Tuple[dict, dict]]
        ) -> 'GetBuilder':
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
        >>> client.query\
        ...     .get('Article', ['title', 'author'])\
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
        >>> client.query\
        ...     .get('Article', ['title', 'author'])\
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
        >>> client.query\
        ...     .get('Article', ['title', 'author'])\
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
        >>> client.query\
        ...     .get('Article', ['title', 'author'])\
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
        >>> client.query\
        ...     .get('Article', ['title', 'author'])\
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
            self._additional['__one_level'].add(properties)
            return self

        if isinstance(properties, list):
            for prop in properties:
                if not isinstance(prop, str):
                    raise TypeError(
                        "If type of 'properties' is `list` then all items must be of type `str`!"
                    )
                self._additional['__one_level'].add(prop)
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

    def build(self) -> str:
        """
        Build query filter as a string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """

        query = '{Get{' + self._class_name
        if self._contains_filter:
            query += '('
            if self._where is not None:
                query += str(self._where)
            if self._limit is not None:
                query += self._limit
            if self._offset is not None:
                query += self._offset
            if self._near_ask is not None:
                query += str(self._near_ask)
            query += ')'

        properties = " ".join(self._properties) + self._additional_to_str()
        if len(properties) != 0:
            query += '{' + properties + '}'
        return query + '}}'

    def _additional_to_str(self) -> str:
        """
        Convert `self._additional` attribute to a `str`.

        Returns
        -------
        str
            The converted self._additional.
        """

        str_to_return = ' _additional {'

        has_values = False
        for one_level in sorted(self._additional['__one_level']):
            has_values = True
            str_to_return += one_level + ' '

        for key, values in sorted(self._additional.items(), key=lambda key_value: key_value[0]):
            if key == '__one_level':
                continue
            has_values = True
            str_to_return += key + ' {'
            for value in sorted(values):
                str_to_return += value + ' '
            str_to_return += '} '

        if has_values is False:
            return ''
        return str_to_return + '}'

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

        clause_with_settings = clause_key + '('
        try:
            for key, value in sorted(settings.items(), key=lambda key_value: key_value[0]):
                if not isinstance(key, str):
                    raise TypeError(
                        "If type of 'properties' is `tuple` then the second elements (<dict>) "
                        "should have all the keys of type `str`!"
                    )
                clause_with_settings += key + ': ' + dumps(value) + ' '
        except TypeError:
            raise TypeError(
                "If type of 'properties' is `tuple` then the second elements (<dict>) "
                "should have all the keys of type `str`!"
            ) from None
        clause_with_settings += ')'

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
