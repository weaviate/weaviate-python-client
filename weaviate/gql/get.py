"""
GraphQL `Get` command.
"""
from typing import List, Union, Optional
from weaviate.gql.filter import WhereFilter, NearText, NearVector, GraphQL, NearObject, Filter
from weaviate.gql.filter import Ask, NearImage
from weaviate.connect import Connection
from weaviate.util import image_encoder_b64


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
        properties : list of str or str
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

        self._class_name = class_name
        self._properties = properties
        self._where: Optional[WhereFilter] = None  # To store the where filter if it is added
        self._limit: Optional[str] = None  # To store the limit filter if it is added
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
        ...     'valueInt': 1000          # value (which is always = to the type of the path property)
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
            Updated GetBuilder.
        """

        self._where = WhereFilter(content)
        self._contains_filter = True
        return self

    def with_near_text(self, content: dict) -> 'GetBuilder':
        """
        Set `nearText` filter. This filter can be used with text modules (text2vec).
        E.g.: text2vec-contextionary, text2vec-transformers.

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
        ...     }
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
        ...     }
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
            Updated GetBuilder.

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
            Updated GetBuilder.

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
            Updated GetBuilder.

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
            string that looks like this: b'BASE64ENCODED` but simple 'BASE64ENCODED`).
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
            Updated GetBuilder.

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
        limit : dict
            The max number of objects returned.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.

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

    def with_ask(self, content: dict) -> 'GetBuilder':
        """
        Ask a question for which weaviate will retreive the answer from your data.
        This filter can be used only with QnA module: qna-transformers.

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
        ...     'properties': <list of str or str>
        ... }

        Full content:

        >>> content = {
        ...     'question' : "What is the NLP?",
        ...     'certainty': 0.7,
        ...     'properties': ['body'] # search the answer in these properties only.
        ... }

        Minimal content:

        >>> content = {
        ...     'question' : "What is the NLP?"
        ... }

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.
        """

        if self._near_ask is not None:
            raise AttributeError("Cannot use multiple 'near' filters, or a 'near' filter along"
                " with a 'ask' filter!")
        self._near_ask = Ask(content)
        self._contains_filter = True
        return self

    def build(self) -> str:
        """
        Build query filter as a string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """

        query = f'{{Get{{{self._class_name}'
        if self._contains_filter:
            query += '('
            if self._where is not None:
                query = query + str(self._where)
            if self._limit is not None:
                query = query + self._limit
            if self._near_ask is not None:
                query = query + str(self._near_ask)
            query += ')'
        query = query + f'{{{" ".join(self._properties)}}}}}}}'

        return query
