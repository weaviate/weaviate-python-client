"""
WCS class definition.
"""
import time
from numbers import Real
from typing import Optional, List, Union, Dict, Tuple

from requests.exceptions import ConnectionError as RequestsConnectionError
from tqdm.auto import tqdm

from weaviate.auth import AuthClientPassword
from weaviate.connect.connection import BaseConnection
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
)


class WCS(BaseConnection):
    """
    WCS class used to create/delete WCS cluster instances.

    Attributes
    ----------
    dev : bool
        True if the WCS instance is for the development console, False if it is for the production
        environment.
    """

    # def __getattr__(self, attr_name):
    #     if attr_name in ('delete', 'get', 'post', 'put', 'patch'):
    #         raise AttributeError
    #     if attr_name in ('_delete', '_get', '_post', '_put', '_patch'):
    #         attr_name = attr_name[1:]
    #     return super().__getattr__(attr_name)

    # def __getattribute__(self, attr_name):
    #     if attr_name in ('delete', 'get', 'post', 'put', 'patch'):
    #         raise AttributeError
    #     if attr_name in ('_delete', '_get', '_post', '_put', '_patch'):
    #         attr_name = attr_name[1:]
    #     return super().__getattribute__(attr_name)

    def __init__(
        self,
        auth_client_secret: AuthClientPassword,
        timeout_config: Union[Tuple[Real, Real], Real] = (2, 20),
        proxies: Union[dict, str, None] = None,
        trust_env: bool = False,
        dev: bool = False,
    ):
        """
        Initialize a WCS class instance.

        Parameters
        ----------
        auth_client_secret : AuthClientPassword
            Authentication credentials for the WCS.
        dev : bool, optional
            Whether to use the development environment, i.e. https://dev.console.semi.technology/.
            If False uses the production environment, i.e. https://console.semi.technology/.
            By default False.
        timeout_config : tuple(Real, Real) or Real, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            real number or, a tuple of two real numbers: (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value, by default (2, 20).
        """

        self.dev = dev

        if dev:
            url = "https://dev.wcs.api.semi.technology"
        else:
            url = "https://wcs.api.semi.technology"

        super().__init__(
            url=url,
            auth_client_secret=auth_client_secret,
            timeout_config=timeout_config,
            proxies=proxies,
            trust_env=trust_env,
            additional_headers=None,
        )
        self._email = auth_client_secret.username

    def __del__(self):
        # in case an exception happens before definition of these members
        if hasattr(self, "_connection"):
            self._connection.close()

    def create(
        self,
        cluster_name: str = None,
        cluster_type: str = "sandbox",
        with_auth: bool = False,
        modules: Optional[Union[str, dict, list]] = None,
        config: dict = None,
        wait_for_completion: bool = True,
    ) -> str:
        """
        Create the cluster and return The Weaviate server URL.

        Parameters
        ----------
        cluster_name : str, optional
            The name of the weaviate cluster to be created, if None a random one is going to be
            generated, by default None.
            NOTE: Case insensitive. The created cluster's name is always lowercased.
        cluster_type : str, optional
            the cluster type/tier, by default 'sandbox'.
        with_auth : bool, optional
            Enable the authentication to the cluster about to be created,
            by default False.
        modules: str or dict or list, optional
            The modules to use, can have multiple modules. One module should look like this:
            >>> {
            ...     "name": "string", # required
            ...     "repo": "string", # optional
            ...     "tag": "string", # optional
            ...     "inferenceUrl": "string" # optional
            ... }
            See the Examples for additional information.
        config : dict, optional
            the cluster configuration. If NOT None then `cluster_name`, `cluster_type`, `module`
            are ignored and the whole cluster configuration should be in this argument,
            by default None. See the Examples below for the complete configuration schema.
        wait_for_completion : bool, optional
            Whether to wait until the cluster is built,
            by default True

        Examples
        --------
        If the `modules` is string then it is going to be used as the MODULE_NAME with a default tag
        for that given MODULE_NAME. If `module` is a dict then it should have the below structure.

        Contextionary:

        >>> {
        ...     "name": "text2vec-contextionary",
        ...     "tag": "en0.16.0-v1.0.0" # this is the default tag
        ... }

        Transformers:

        >>> {
        ...     "name": "text2vec-transformers",
        ...     "tag": "sentence-transformers-paraphrase-MiniLM-L6-v2"
        ... }

        Both the examples above use the 'semitechnologies' repo (which is the default one).
        The `modules` also can be a list of individual module configuration that conforms to the
        above description.

        The COMPLETE `config` argument looks like this:

        >>> {
        ...     "email": "user@example.com",
        ...     "configuration": {
        ...         "requiresAuthentication": true,
        ...         "c11yTag": "string",
        ...         "tier": "string",
        ...         "supportLevel": "string",
        ...         "region": "string",
        ...         "release": {
        ...             "chart": "latest",
        ...             "weaviate": "latest"
        ...         },
        ...         "modules": [
        ...             {
        ...                 "name": "string",
        ...                 "repo": "string",
        ...                 "tag": "string",
        ...                 "inferenceUrl": "string"
        ...             }
        ...         ],
        ...         "backup": {
        ...             "activated": false
        ...         },
        ...         "restore": {
        ...             "name": "string"
        ...         }
        ...     },
        ...     "id": "string"
        ... }

        Returns
        -------
        str
            The URL of the create Weaviate server cluster.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If creating the weaviate cluster failed for a different reason,
            more information is given in the exception.
        TypeError
            If `config` is neither None nor of type 'dict'.
        TypeError
            If `modules` argument is of a wrong type.
        KeyError
            If one of the `modules` does not conform to the module schema.
        TypeError
            In case `modules` is a list and one module has a wrong type.
        TypeError
            In case one of the modules is of type dict and the values are not of type 'str'.
        """

        if cluster_name is not None:
            cluster_name = cluster_name.lower()

        if config is None:
            config = {
                "id": cluster_name,
                "configuration": {"tier": cluster_type, "requiresAuthentication": with_auth},
            }
            config["configuration"]["modules"] = _get_modules_config(modules)
        else:
            if not isinstance(config, dict):
                raise TypeError(
                    "The `config` argument must be either None or of type 'dict', given: "
                    f"{type(config)}"
                )
            if "id" in config:
                cluster_name = config["id"].lower()

        try:
            response = self.post(path="/clusters", weaviate_object=config)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("WCS cluster was not created.") from conn_err
        if response.status_code == 400 and "already exists" in response.text:
            # this line is never executed if cluster_name is None
            return "https://" + self.get_cluster_config(cluster_name)["meta"]["PublicURL"]

        if response.status_code != 202:
            raise UnexpectedStatusCodeException("Creating WCS instance", response)

        cluster_name = response.json()["id"]

        if wait_for_completion is True:
            title_bar = tqdm(
                bar_format="{desc}",
                desc="Creating cluster:",
                leave=True,
            )
            progress_bar = tqdm(
                total=100.0,
                leave=True,
                unit="%",
                bar_format=(
                    "{percentage:3.0f}% |{bar}|[{elapsed}<{remaining}, {rate_fmt}{postfix}]"
                ),
            )
            progress = 0
            while progress != 100:
                time.sleep(2.0)
                progress_state = self.get_cluster_config(cluster_name)["status"]["state"]
                progress = progress_state["percentage"]
                progress_bar.update(progress - progress_bar.n)
                title_bar.set_description(progress_state.get("message"))
            title_bar.close()
            progress_bar.close()

        return "https://" + self.get_cluster_config(cluster_name)["meta"]["PublicURL"]

    def is_ready(self, cluster_name: str) -> bool:
        """
        Check if the cluster is created.

        Parameters
        ----------
        cluster_name : str
            The name of the weaviate server cluster.
            NOTE: Case insensitive. The WCS cluster's name is always lowercased.

        Returns
        -------
        bool
            True if cluster is created and ready to use, False otherwise.
        """

        cluster_name = cluster_name.lower()
        response = self.get_cluster_config(cluster_name)
        if response == {}:
            raise ValueError(f"No cluster with name: '{cluster_name}'. Check the name again!")
        if response["status"]["state"]["percentage"] == 100:
            return True
        return False

    def get_clusters(self) -> Optional[List[str]]:
        """
        Lists all weaviate clusters registered with the this account.

        Returns
        -------
        Optional[List[str]]
            A list of cluster names or None if no clusters.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If getting the weaviate clusters failed for a different reason,
            more information is given in the exception.
        """

        try:
            response = self.get(
                path="/clusters/list",
                params={"email": self._email},
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("WCS clusters were not fetched.") from conn_err
        if response.status_code == 200:
            return response.json()["clusterIDs"]
        raise UnexpectedStatusCodeException("Checking WCS instance", response)

    def get_cluster_config(self, cluster_name: str) -> dict:
        """
        Get details of a cluster.

        Parameters
        ----------
        cluster_name : str
            The name of the weaviate server cluster.
            NOTE: Case insensitive. The WCS cluster's name is always lowercased.

        Returns
        -------
        dict
            Details in a JSON format. If no cluster with such name was found then an empty
            dictionary is returned.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If getting the weaviate cluster failed for a different reason,
            more information is given in the exception.
        """

        try:
            response = self.get(
                path="/clusters/" + cluster_name.lower(),
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("WCS cluster info was not fetched.") from conn_err
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return {}
        raise UnexpectedStatusCodeException("Checking WCS instance", response)

    def delete_cluster(self, cluster_name: str) -> None:
        """
        Delete the WCS Weaviate cluster instance.

        Parameters
        ----------
        cluster_name : str
            The name of the weaviate server cluster.
            NOTE: Case insensitive. The WCS cluster's name is always lowercased.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If deleting the weaviate cluster failed for a different reason,
            more information is given in the exception.
        """

        try:
            response = self.delete(
                path="/clusters/" + cluster_name.lower(),
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("WCS cluster was not deleted.") from conn_err
        if response.status_code in (200, 404):
            return
        raise UnexpectedStatusCodeException("Deleting WCS instance", response)

    def get_users_of_cluster(self, cluster_name: str) -> list:
        """
        Get users of the WCS Weaviate cluster instance.

        Parameters
        ----------
        cluster_name : str
            The name of the Weaviate server cluster.
            NOTE: Case insensitive. The WCS cluster's name is always lowercased.

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnsuccessfulStatusCodeError
            If deleting the Weaviate cluster failed for a different reason,
            more information is given in the exception.

        Returns
        -------
        list
            The list of users.
        """

        path = f"/clusters/{cluster_name.lower()}/users"

        try:
            response = self.get(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Could not get users of the cluster due to connection error."
            ) from conn_err
        if response.status_code == 200:
            return response.json()["users"]
        raise UnexpectedStatusCodeException("Getting cluster's users", response)

    def add_user_to_cluster(self, cluster_name: str, user: str) -> None:
        """
        Add user to the WCS Weaviate cluster instance.

        Parameters
        ----------
        cluster_name : str
            The name of the Weaviate server cluster.
            NOTE: Case insensitive. The WCS cluster's name is always lowercased.
        user:
            The user to be added to WCS Weaviate cluster instance.

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnsuccessfulStatusCodeError
            If deleting the Weaviate cluster failed for a different reason,
            more information is given in the exception.
        """

        path = f"/clusters/{cluster_name.lower()}/users/{user}"

        try:
            response = self.post(
                path=path,
                weaviate_object=None,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Could not add user of the cluster due to connection error."
            ) from conn_err
        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeException("Adding user to cluster", response)

    def remove_user_from_cluster(self, cluster_name: str, user: str) -> None:
        """
        Remove user from the WCS Weaviate cluster instance.

        Parameters
        ----------
        cluster_name : str
            The name of the Weaviate server cluster.
            NOTE: Case insensitive. The WCS cluster's name is always lowercased.
        user:
            The user to be removed from WCS Weaviate cluster instance.

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnsuccessfulStatusCodeError
            If deleting the Weaviate cluster failed for a different reason,
            more information is given in the exception.
        """

        path = f"/clusters/{cluster_name.lower()}/users/{user}"

        try:
            response = self.delete(
                path=path,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Could not remove user from the cluster due to connection error."
            ) from conn_err
        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeException("Removing user from cluster", response)


def _get_modules_config(modules: Optional[Union[str, dict, list]]) -> List[Dict[str, str]]:
    """
    Get an WCS modules configuration format.

    Parameters
    ----------
    modules : Optional[str, dict, list]
        The modules information from which to construct the modules configuration.

    Returns
    -------
    List[Dict[str, str]]
        The modules configuration as a list.

    Raises
    ------
    TypeError
        If `modules` argument is of a wrong type.
    KeyError
        If one of the `modules` does not conform to the module schema.
    TypeError
        In case `modules` is a list and one module has a wrong type.
    TypeError
        In case one of the modules is of type dict and the values are not of type 'str'.
    """

    def get_module_dict(module: Union[Dict[str, str], str]) -> Dict[str, str]:
        """
        Local function to validate each module configuration.

        Parameters
        ----------
        _module : Union[dict, str]
            The module configuration to be validated.

        Returns
        -------
        Dict[str, str]
            The configuration of the module as a dictionary.
        """

        if isinstance(module, str):
            # only module name
            return {"name": module}

        if isinstance(module, dict):
            # module config
            if "name" not in module or not set(module).issubset(
                ["name", "tag", "repo", "inferenceUrl"]
            ):
                raise KeyError(
                    "A module should have a required key: 'name',  and optional keys: 'tag', "
                    f"'repo' and/or 'inferenceUrl'! Given keys: {module.keys()}"
                )
            for key, value in module.items():
                if not isinstance(value, str):
                    raise TypeError(
                        "The type of each value of the module's dict should be 'str'! "
                        f"The key '{key}' has type: {type(value)}"
                    )
            return module

        raise TypeError(
            "Wrong type for one of the modules. Should be either 'str' or 'dict' but given: "
            f"{type(module)}"
        )

    if modules is None:
        # no module
        return []

    if isinstance(modules, (str, dict)):
        return [get_module_dict(modules)]
    if isinstance(modules, list):
        to_return = []
        for _module in modules:
            to_return.append(get_module_dict(_module))
        return to_return

    raise TypeError(
        "Wrong type for the `modules` argument. Accepted types are: NoneType, 'str', 'dict' or "
        f"`list` but given: {type(modules)}"
    )
