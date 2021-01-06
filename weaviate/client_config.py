from typing import Tuple

class ClientConfig:
    """
    Allows to configure the client with additional parameters.
    """

    def __init__(self, timeout_config: Tuple[int, int]=(2, 20)):
        """
        Initialize a ClientConfig class instance.

        Parameters
        ----------
        timeout_config : tuple of int, optional
            Set the timeout config as a tuple of (retries, time out seconds),
            by default (2, 20).
        """

        self.timeout_config = timeout_config
