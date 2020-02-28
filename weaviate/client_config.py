

class ClientConfig:
    """ Allows to configure the client with additional parameters
    """

    def __init__(self, timeout_config=(2, 20)):
        """

        :param timeout_config: Set the timeout config as a tuple of (retries, time out seconds)
        :type timeout_config: tuple of int
        """
        self.timeout_config = timeout_config
