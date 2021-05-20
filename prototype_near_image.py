
class NearImage(Filter):
    """
    NearObject class used to filter weaviate objects.
    """

    def __init__(self, content: dict):
        """
        Initialize a NearImage class instance.

        Parameters
        ----------
        content : list
            The content of the `nearImage` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If 'content'  has key "certainty" but the value is not float.
        """

        super().__init__(content)

        if 'image' not in content:
            raise ValueError('"content" is missing the mandatory key "image"!')

        if "certainty" in content:
            _check_certainty_type(content["certainty"])

        self._content = deepcopy(content)
        self._content['image'] = image_encoder(content['image'])

    def __str__(self):
        near_image = f'nearImage: {{image: {self._content["image"]}'
        if 'certainty' in self._content:
            near_image += f' certainty: {self._content["certainty"]}'
        return near_image + '} '


import base64
from io import BufferedReader, BufferedRandom

def image_encoder(image_or_image_path: Union[str, BufferedReader, BufferedRandom]) -> str:
    """
    Encode a image in a Weaviate understandable format from a binary read file or by providing
    the image path.

    Parameters
    ----------
    image_or_image_path : str, io.BufferedReader, io.BufferedRandom
        The binary read file or the path to the file.

    Returns
    -------
    str
        Encoded image.

    Raises
    ------
    ValueError
        If the argument is str and does not point to an existing file.
    TypeError
        If the argument is of a wrong data type. 
    """


    if isinstance(image_or_image_path, str):

        if image_or_image_path.startswith("data:image/jpeg;base64,"):
            # image is already in weaviate format
            return image_or_image_path
        
        if not os.path.isfile(image_or_image_path):
            raise ValueError("No file found at location " + image_or_image_path)
        file = open(image_or_image_path, 'br')
        
    elif isinstance(image_or_image_path, (BufferedReader, BufferedRandom)):
        file = image_or_image_path
    else:
        raise TypeError('"image_or_image_path" should be a image path or a binary file'
            ' (io.BufferedReader or io.BufferedRandom)')

    return f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("ascii")}'

def image_decoder(encoded_image: str) -> str:
    """
    Decode image from a Weaviate format image.

    Parameters
    ----------
    encoded_image : str
        The encoded image.

    Returns
    -------
    str
        Decoded image as a binary string.
    """

    return base64.b64decode(encoded_image.strip('data:image/jpeg;base64,'))