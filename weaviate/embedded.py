import hashlib
import os
import platform
import re
import socket
import stat
import subprocess
import tarfile
import time
import urllib.request
import warnings
import zipfile
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
import validators

from weaviate import exceptions
from weaviate.exceptions import WeaviateStartUpError
from weaviate.logger import logger
from weaviate.util import _decode_json_response_dict

DEFAULT_BINARY_PATH = str(Path.home() / ".cache/weaviate-embedded/")
DEFAULT_PERSISTENCE_DATA_PATH = str(Path.home() / ".local/share/weaviate")
GITHUB_RELEASE_DOWNLOAD_URL = "https://github.com/weaviate/weaviate/releases/download/"

DEFAULT_PORT = 8079
DEFAULT_GRPC_PORT = 50060

WEAVIATE_VERSION = "1.26.6"


@dataclass
class EmbeddedOptions:
    persistence_data_path: str = os.environ.get("XDG_DATA_HOME", DEFAULT_PERSISTENCE_DATA_PATH)
    binary_path: str = os.environ.get("XDG_CACHE_HOME", DEFAULT_BINARY_PATH)
    version: str = WEAVIATE_VERSION
    port: int = DEFAULT_PORT
    hostname: str = "127.0.0.1"
    additional_env_vars: Optional[Dict[str, str]] = None
    grpc_port: int = DEFAULT_GRPC_PORT


def get_random_port() -> int:
    sock = socket.socket()
    sock.bind(("", 0))
    port_num = int(sock.getsockname()[1])
    sock.close()
    return port_num


class _EmbeddedBase:
    def __init__(self, options: EmbeddedOptions) -> None:
        self.options = options
        self.grpc_port: int = options.grpc_port
        self.process: Optional[subprocess.Popen[bytes]] = None
        self.ensure_paths_exist()
        self.check_supported_platform()
        self._parsed_weaviate_version = ""
        # regular expression to detect a version number: v[one digit].[1-2 digits].[1-2 digits]
        # optionally there can be a "-rc/alpha/beta.[1-2 digits]"
        # nothing in front or back
        version_pattern = re.compile(
            r"^\d\.\d{1,2}\.\d{1,2}?(-rc\.\d{1,2}|-beta\.\d{1,2}|-alpha\.\d{1,2}|$)$"
        )

        valid_url = validators.url(self.options.version)
        if isinstance(valid_url, validators.ValidationError):
            valid_url = validators.url(self.options.version, simple_host=True)  # for localhost
        if valid_url:
            if not self.options.version.endswith(".tar.gz") and not self.options.version.endswith(
                ".zip"
            ):
                raise exceptions.WeaviateEmbeddedInvalidVersionError(self.options.version)

            # for GitHub urls we can parse the version from the url
            if self.options.version.startswith(GITHUB_RELEASE_DOWNLOAD_URL):
                # replace with str.removeprefix() after 3.8 has been deprecated
                self._parsed_weaviate_version = self.options.version[
                    len(GITHUB_RELEASE_DOWNLOAD_URL) :
                ].split("/")[0]
            self._download_url = self.options.version
        elif version_pattern.match(self.options.version):
            version_tag = "v" + self.options.version
            self._parsed_weaviate_version = version_tag
            self._set_download_url_from_version_tag(version_tag)
        elif self.options.version == "latest":
            response = httpx.get("https://api.github.com/repos/weaviate/weaviate/releases/latest")
            latest = _decode_json_response_dict(response, "get tag of latest weaviate release")
            assert latest is not None
            self._set_download_url_from_version_tag(latest["tag_name"])
        else:
            raise exceptions.WeaviateEmbeddedInvalidVersionError(self.options.version)

    def _set_download_url_from_version_tag(self, version: str) -> None:
        if platform.system() == "Darwin":
            machine_type = "all"
            package_format = "zip"
        else:
            machine_type = platform.machine()
            if machine_type == "x86_64":
                machine_type = "amd64"
            elif machine_type == "aarch64":
                machine_type = "arm64"
            package_format = "tar.gz"

        self._download_url = (
            GITHUB_RELEASE_DOWNLOAD_URL
            + version
            + "/weaviate-"
            + version
            + "-"
            + platform.system()
            + "-"
            + machine_type
            + "."
            + package_format
        )

    def __del__(self) -> None:
        self.stop()

    def ensure_paths_exist(self) -> None:
        Path(self.options.binary_path).mkdir(parents=True, exist_ok=True)
        Path(self.options.persistence_data_path).mkdir(parents=True, exist_ok=True)

    def ensure_weaviate_binary_exists(self) -> None:
        self._weaviate_binary_path = Path(
            self.options.binary_path,
            "weaviate-"
            + self._parsed_weaviate_version
            + "-"
            + str(hashlib.sha256(self.options.version.encode("utf-8")).hexdigest()),
        )
        if not self._weaviate_binary_path.exists():
            logger.info(
                f"Binary {self.options.binary_path} did not exist. Downloading binary from {self._download_url}"
            )
            if self._download_url.endswith(".tar.gz"):
                tar_filename = Path(self.options.binary_path, "tmp_weaviate.tgz")
                urllib.request.urlretrieve(self._download_url, tar_filename)
                with tarfile.open(tar_filename) as binary_tar:
                    binary_tar.extract("weaviate", path=Path(self.options.binary_path))
                tar_filename.unlink()
            else:
                assert self._download_url.endswith(".zip")
                zip_filename = Path(self.options.binary_path, "tmp_weaviate.zip")
                urllib.request.urlretrieve(self._download_url, zip_filename)
                with zipfile.ZipFile(zip_filename, "r") as zip_ref:
                    zip_ref.extract("weaviate", path=Path(self.options.binary_path))

            (Path(self.options.binary_path) / "weaviate").rename(self._weaviate_binary_path)

            # Ensuring weaviate binary is executable
            self._weaviate_binary_path.chmod(
                self._weaviate_binary_path.stat().st_mode | stat.S_IEXEC
            )

    def wait_till_listening(self) -> None:
        seconds = 30
        sleep_interval = 0.1
        retries = int(seconds / sleep_interval)
        while self.is_listening() is False and retries > 0:
            time.sleep(sleep_interval)
            retries -= 1
        if retries == 0:
            raise WeaviateStartUpError(
                f"Embedded DB did not start listening on port {self.options.port} within {seconds} seconds"
            )

    @staticmethod
    def check_supported_platform() -> None:
        if platform.system() in ["Windows"]:
            raise WeaviateStartUpError(
                f"""{platform.system()} is not supported with EmbeddedDB. Please upvote this feature request if you want
                 this: https://github.com/weaviate/weaviate/issues/3315"""  # noqa: E231
            )

    def stop(self) -> None:
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.wait()
            except ProcessLookupError:
                logger.info(
                    f"""Tried to stop embedded weaviate process {self.process.pid}. Process was not found. So not doing
                    anything"""
                )
            self.process = None

    def ensure_running(self) -> None:
        if self.is_listening() is False:
            logger.info(
                f"Embedded weaviate wasn't listening on ports http:{self.options.port} & grpc:{self.options.grpc_port}, so starting embedded weaviate again"
            )
            self.start()

    def start(self) -> None:
        self.ensure_weaviate_binary_exists()
        my_env = os.environ.copy()

        my_env.setdefault("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
        my_env.setdefault("QUERY_DEFAULTS_LIMIT", "20")
        my_env.setdefault("PERSISTENCE_DATA_PATH", self.options.persistence_data_path)
        my_env.setdefault("PROFILING_PORT", str(get_random_port()))
        # Limitation with weaviate server requires setting
        # data_bind_port to gossip_bind_port + 1
        gossip_bind_port = get_random_port()
        data_bind_port = gossip_bind_port + 1
        my_env.setdefault("CLUSTER_GOSSIP_BIND_PORT", str(gossip_bind_port))
        my_env.setdefault("CLUSTER_DATA_BIND_PORT", str(data_bind_port))
        my_env.setdefault("GRPC_PORT", str(self.grpc_port))
        my_env.setdefault("RAFT_BOOTSTRAP_EXPECT", str(1))
        my_env.setdefault("CLUSTER_IN_LOCALHOST", str(True))

        # Each call to `get_random_port()` will likely result in
        # a port 1 higher than the last time it was called. With
        # this, we end up with raft_port == gossip_bind_port + 1,
        # which is the same as data_bind_port. This kind of
        # configuration leads to failed cross cluster communication.
        # Although the current version of embedded does not support
        # multi-node instances, the backup process communication
        # passes through the internal cluster server, and will fail.
        #
        # So we here we ensure that raft_port never collides with
        # data_bind_port.
        raft_port = data_bind_port + 1
        raft_internal_rpc_port = raft_port + 1
        my_env.setdefault("RAFT_PORT", str(raft_port))
        my_env.setdefault("RAFT_INTERNAL_RPC_PORT", str(raft_internal_rpc_port))

        my_env.setdefault(
            "ENABLE_MODULES",
            "text2vec-openai,text2vec-cohere,text2vec-huggingface,ref2vec-centroid,generative-openai,qna-openai,"
            "reranker-cohere",
        )

        # have a deterministic hostname in case of changes in the network name.
        # This allows to run multiple parallel instances
        cluster_hostname = f"Embedded_at_{self.options.port}"
        my_env.setdefault("CLUSTER_HOSTNAME", cluster_hostname)
        my_env.setdefault("RAFT_JOIN", f"{cluster_hostname}:{raft_port}")

        if self.options.additional_env_vars is not None:
            my_env.update(self.options.additional_env_vars)

        # filter warning about running processes.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            process = subprocess.Popen(
                [
                    f"{self._weaviate_binary_path}",
                    "--host",
                    self.options.hostname,
                    "--port",
                    str(self.options.port),
                    "--scheme",
                    "http",
                    "--read-timeout=600s",
                    "--write-timeout=600s",
                ],
                env=my_env,
            )
            self.process = process
        logger.info(f"Started {self.options.binary_path}: process ID {self.process.pid}")
        self.wait_till_listening()

    @abstractmethod
    def is_listening(self) -> bool:
        raise NotImplementedError()


class EmbeddedV3(_EmbeddedBase):
    def is_listening(self) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.options.hostname, self.options.port))
            return True
        except (socket.error, ConnectionRefusedError):
            return False
        finally:
            s.close()

    def start(self) -> None:
        if self.is_listening():
            logger.info(f"embedded weaviate is already listening on port {self.options.port}")
            return
        super().start()


EmbeddedDB = EmbeddedV3  # needed for BC from v3 -> v4


class EmbeddedV4(_EmbeddedBase):
    def is_listening(self) -> bool:
        up = self.__is_listening()
        return up[0] and up[1]

    def __is_listening(self) -> Tuple[bool, bool]:
        http_listening, grpc_listening = False, False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.options.hostname, self.options.port))
                http_listening = True
            except (socket.error, ConnectionRefusedError):
                pass
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.options.hostname, self.grpc_port))
                grpc_listening = True
            except (socket.error, ConnectionRefusedError):
                pass
        return (http_listening, grpc_listening)

    def start(self) -> None:
        up = self.__is_listening()
        if up[0] and up[1]:
            raise WeaviateStartUpError(
                f"Embedded DB did not start because processes are already listening on ports http:{self.options.port} and grpc:{self.grpc_port}"
                f"use weaviate.connect_to_local(port={self.options.port}, grpc_port={self.options.grpc_port}) to connect to the existing instance"
            )
        elif up[0] and not up[1]:
            raise WeaviateStartUpError(
                f"Embedded DB did not start because a process is already listening on port http:{self.options.port}"
                "look for another free port for the HTTP connection to you embedded instance"
            )
        elif up[1] and not up[0]:
            raise WeaviateStartUpError(
                f"Embedded DB did not start because a process is already listening on port grpc:{self.grpc_port}"
                "look for another free port for the gRPC connection to your embedded instance"
            )
        super().start()
