from typing import Tuple, Union, List

class ClientConfig:
    """
    Allows to configure the client with additional parameters.
    """

    def __init__(self, timeout_config: Union[Tuple[int, int], List[int]]=(2, 20)):
        """
        Initialize a ClientConfig class instance.

        Parameters
        ----------
        timeout_config : tuple of int or list of int, optional
            Set the timeout config as a tuple of (retries, time out seconds),
            by default (2, 20).

        Raises
        ------
        TypeError
            If arguments are of a wrong data type.
        ValueError
            If 'timeout_config' is not a tuple of 2.
        """

        if not (isinstance(timeout_config, tuple) or isinstance(timeout_config, list)):
            raise TypeError("'timeout_config' should be either a tuple or a list!")
        if len(timeout_config) != 2:
            raise ValueError("'timeout_config' must be of length 2!")
        if not (isinstance(timeout_config[0], int) and isinstance(timeout_config[1], int)):
            raise TypeError("'timeout_config' must be tupel of int")

        self.timeout_config = tuple(timeout_config)
