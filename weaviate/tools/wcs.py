import time
from typing import Optional, List, Union
import json
import sys
import requests
from tqdm import tqdm
import weaviate
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.auth import AuthCredentials


class WCS(weaviate.connect.Connection):
    """
    WCS class used to create/delete WCS cluster instances.

    Attributes
    ----------
    dev : bool
        True if the WCS instance is for the development console, False if it is for the production
        environment.
    """

    is_authentication_required = True

    def __init__(self, auth_client_secret: AuthCredentials, dev: bool=False):
        """
        Initialize a WCS class instance.

        Parameters
        ----------
        auth_client_secret : AuthCredentials
            Authentication credentials for the WCS.
        dev : bool, optional
            Whether to use the development environment, i.e. https://dev.console.semi.technology/.
            If False uses the production environment, i.e. https://console.semi.technology/.
            By default False.
        """

        self._timeout_config = (2, 20)
        self.auth_expires = 0  # unix time when auth expires
        self.auth_bearer = 0
        self.auth_client_secret = auth_client_secret
        self.dev = dev
        if dev:
            url = 'https://dev.wcs.api.semi.technology'
        else:
            url = 'https://wcs.api.semi.technology'
        self.url = url + '/v1/clusters'

        auth_path = (url.replace('://', '://auth.') +
            '/auth/realms/SeMI/.well-known/openid-configuration')

        # make _refresh_authentication method to point to _set_bearer method.
        self._refresh_authentication = lambda: self._set_bearer('wcs', auth_path)

        if isinstance(auth_client_secret, AuthCredentials):
            self._refresh_authentication()
        else:
            raise ValueError("No login credentials provided.")

    def create(self,
            cluster_name: str=None,
            cluster_type: str='sandbox',
            module: Optional[Union[str, dict]]=None,
            config: dict=None,
            wait_for_completion: bool=True
        ) -> str:
        """
        Create the cluster and return a Weaviate Client instance that is connected to that cluster.

        Parameters
        ----------
        cluster_name : str, optional
            Name of the weaviate cluster, if None a random one is going to be generated,
            by default None
        cluster_type : str, optional
            Cluster type, by default 'sandbox'.
        module: str or dict, optional
            The vectorizer module to use. Supported only on DEV environment WCS.
            The module configuration looks like this:
            {"name": MODULE_NAME, "tag": MODULE_TAG}
            See examples below.
        config : dict, optional
            Cluster configuration. If it is NOT None then `cluster_name`, `cluster_type`,
            `module` are ignored and the whole cluster configuration should be in this argument,
            by default None
        wait_for_completion : bool, optional
            Whether to wait until the cluster is built,
            by default True

        Examples
        --------
        If the `module` is str then it is going to beused as the MODULE_NAME with a default tag
        for that given MODULE_NAME. If `module` is a dict then it should have the above
        structure.

        Contextionary:

        >>> { 
        ...     "name": "text2vec-contextionary",
        ...     "tag": "en0.16.0-v1.0.0" # this is the default tag
        ... }

        Transformers:

        >>> { 
        ...     "name": "text2vec-transformers",
        ...     "tag": "distilbert-base-uncased" # or another transformer model from 
        ...                                         # https://huggingface.co/models
        ... }

        Returns
        -------
        str
            The URL of the create cluster.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If creating the weaviate cluster failed for a different reason,
            more information is given in the exception.
        """

        if config is None:
            config = {
                'id': cluster_name,
                'configuration': {
                    'tier': cluster_type,
                }
            }
            if self.dev:
                config['configuration']['modules'] = _get_module_config(module)

        data_to_send = json.dumps(config).encode("utf-8")

        try:
            response = requests.post(
                url=self.url,
                data=data_to_send,
                headers=self._get_request_header(),
                timeout=self._timeout_config
            )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, WCS cluster was not created.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 400 and "already exists" in response.text:
            # this line is never executed if cluster_name is None
            return 'https://' + self.get_cluster_config(cluster_name)['meta']['PublicURL']

        if response.status_code != 202:
            raise UnexpectedStatusCodeException('Creating WCS instance', response)

        if cluster_name is None:
            cluster_name = response.json()['id']

        if wait_for_completion is True:
            pbar = tqdm(total=100)
            progress = 0
            while progress != 100:
                time.sleep(2.0)
                progress = self.get_cluster_config(cluster_name)["status"]["state"]["percentage"]
                pbar.update(progress - pbar.n)
            pbar.close()

        return 'https://' + self.get_cluster_config(cluster_name)['meta']['PublicURL']

    def is_ready(self, cluster_name: str) -> bool:
        """
        Check if the cluster is created.

        Parameters
        ----------
        cluster_name : str
            Name of the weaviate cluster.

        Returns
        -------
        bool
            True if cluster is created and ready to use, False otherwise.
        """

        response = self.get_cluster_config(cluster_name)
        if response["status"]["state"]["percentage"] == 100:
            return True
        return False

    def get_clusters(self, email: str) -> Optional[List[str]]:
        """
        Lists all weaviate clusters registerd with the 'email'.

        Parameters
        ----------
        email : str
            The email for which to get cluster names.

        Returns
        -------
        Optional[List[str]]
            A list of cluster names or None if no clusters.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If getting the weaviate clusters failed for a different reason,
            more information is given in the exception.
        """

        try:
            response = requests.get(
                url=self.url + '/list',
                headers=self._get_request_header(),
                timeout=self._timeout_config,
                params={
                    'email': email
                }
            )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, WCS clusters were not fetched.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()['clusterIDs']
        raise UnexpectedStatusCodeException('Checking WCS instance', response)

    def get_cluster_config(self, cluster_name: str) -> dict:
        """
        Get details of a cluster.

        Parameters
        ----------
        cluster_name : str
            Name of the weaviate cluster.

        Returns
        -------
        dict
            Details in a JSON format.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If getting the weaviate cluster failed for a different reason,
            more information is given in the exception.
        """

        try:
            response = requests.get(
                url=f'{self.url}/{cluster_name}',
                headers=self._get_request_header(),
                timeout=self._timeout_config
            )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, WCS cluster info was not fetched.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException('Checking WCS instance', response)

    def delete(self, cluster_name: str) -> None:
        """
        Delete the WCS instance.

        Parameters
        ----------
        cluster_name : str
            Name of the weaviate cluster.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.exceptions.UnexpectedStatusCodeException
            If deleting the weaviate cluster failed for a different reason,
            more information is given in the exception.
        """

        try:
            response = requests.delete(
                url=f'{self.url}/{cluster_name}',
                headers=self._get_request_header(),
                timeout=self._timeout_config
            )
        except RequestsConnectionError as conn_err:
            message = str(conn_err)\
                    + ' Connection error, WCS cluster was not deleted.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])

        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeException('Deleting WCS instance', response)

def _get_module_config(module: Optional[Union[str, dict]]) -> list:
    """
    Get an WCS module configuration format.

    Parameters
    ----------
    module : Optional[str, dict]
        The module information from which to construct the module configuration.

    Resurns
    -------
    list
        The module configuration as a list.

    Raises
    ------
    KeyError
        If `module` is of type dict and does not contain the required key 'name' and the optional
        'tag' key only.
    TypeError
        If `module` is of a wrong type.
    """

    if module is None:
        # no module
        return []

    if isinstance(module, str):
        # only module name
        return [
            {
                'name': module
            }
        ]

    if isinstance(module, dict):
        # module config
        if 'name' in module and set(module).issubset(['name', 'tag']):
            return [module]
        raise KeyError("`module` should have a required 'name' key and an optional 'tag' key!")
    raise TypeError('Wrong type for `module`, accepted types are str, dict and None!')
