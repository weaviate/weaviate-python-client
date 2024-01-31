import datetime
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Tuple, TypeVar, Union, cast, overload
from urllib.parse import urlparse

import grpc  # type: ignore
from grpc import Channel, ssl_channel_credentials
from grpc.aio import Channel as AsyncChannel  # type: ignore

from pydantic import BaseModel, field_validator, model_validator

from weaviate.types import NUMBER


JSONPayload = Union[dict, list]
TIMEOUT_TYPE_RETURN = Tuple[NUMBER, NUMBER]
PYPI_TIMEOUT = 0.1
MAX_GRPC_MESSAGE_LENGTH = 104858000  # 10mb, needs to be synchronized with GRPC server
GRPC_OPTIONS = [
    ("grpc.max_send_message_length", MAX_GRPC_MESSAGE_LENGTH),
    ("grpc.max_receive_message_length", MAX_GRPC_MESSAGE_LENGTH),
]


@dataclass
class _Timeout:
    connect: int
    read: int

    @classmethod
    def from_timeout_config(cls, timeout: TIMEOUT_TYPE_RETURN) -> "_Timeout":
        return cls(
            connect=int(timeout[0]),
            read=int(timeout[1]),
        )


class ProtocolParams(BaseModel):
    host: str
    port: int
    secure: bool

    @field_validator("host")
    def _check_host(cls, v: str) -> str:
        if v == "":
            raise ValueError("host must not be empty")
        return v

    @field_validator("port")
    def _check_port(cls, v: int) -> int:
        if v < 0 or v > 65535:
            raise ValueError("port must be between 0 and 65535")
        return v


T = TypeVar("T", bound="ConnectionParams")


class ConnectionParams(BaseModel):
    http: ProtocolParams
    grpc: ProtocolParams

    @classmethod
    def from_url(cls, url: str, grpc_port: int, grpc_secure: bool = False) -> "ConnectionParams":
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ["http", "https"]:
            raise ValueError(f"Unsupported scheme: {parsed_url.scheme}")
        if parsed_url.port is None:
            port = 443 if parsed_url.scheme == "https" else 80
        else:
            port = parsed_url.port

        return cls(
            http=ProtocolParams(
                host=cast(str, parsed_url.hostname),
                port=port,
                secure=parsed_url.scheme == "https",
            ),
            grpc=ProtocolParams(
                host=cast(str, parsed_url.hostname),
                port=grpc_port,
                secure=grpc_secure or parsed_url.scheme == "https",
            ),
        )

    @classmethod
    def from_params(
        cls,
        http_host: str,
        http_port: int,
        http_secure: bool,
        grpc_host: str,
        grpc_port: int,
        grpc_secure: bool,
    ) -> "ConnectionParams":
        return cls(
            http=ProtocolParams(
                host=http_host,
                port=http_port,
                secure=http_secure,
            ),
            grpc=ProtocolParams(
                host=grpc_host,
                port=grpc_port,
                secure=grpc_secure,
            ),
        )

    @model_validator(mode="after")
    def _check_port_collision(self: T) -> T:
        if self.http.host == self.grpc.host and self.http.port == self.grpc.port:
            raise ValueError("http.port and grpc.port must be different if using the same host")
        return self

    @property
    def _grpc_address(self) -> Tuple[str, int]:
        return (self.grpc.host, self.grpc.port)

    @property
    def _grpc_target(self) -> str:
        return f"{self.grpc.host}:{self.grpc.port}"

    @overload
    def _grpc_channel(self, async_channel: Literal[False]) -> Channel:
        ...

    @overload
    def _grpc_channel(self, async_channel: Literal[True]) -> AsyncChannel:
        ...

    def _grpc_channel(self, async_channel: bool) -> Union[Channel, AsyncChannel]:
        if async_channel:
            import_path = grpc.aio
        else:
            import_path = grpc

        if self.grpc.secure:
            return import_path.secure_channel(
                target=self._grpc_target,
                credentials=ssl_channel_credentials(),
                options=GRPC_OPTIONS,
            )
        else:
            return import_path.insecure_channel(
                target=self._grpc_target,
                options=GRPC_OPTIONS,
            )

    @property
    def _http_scheme(self) -> str:
        return "https" if self.http.secure else "http"

    @property
    def _http_url(self) -> str:
        return f"{self._http_scheme}://{self.http.host}:{self.http.port}"


class _ConnectionBase(ABC):
    @abstractmethod
    def get_current_bearer_token(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_proxies(self) -> dict:
        raise NotImplementedError


def _get_proxies(proxies: Union[dict, str, None], trust_env: bool) -> dict:
    """
    Get proxies as dict, compatible with 'requests' library.
    NOTE: 'proxies' has priority over 'trust_env', i.e. if 'proxies' is NOT None, 'trust_env'
    is ignored.

    Parameters
    ----------
    proxies : dict, str or None
        The proxies to use for requests. If it is a dict it should follow 'requests' library
        format (https://docs.python-requests.org/en/stable/user/advanced/#proxies). If it is
        a URL (str), a dict will be constructed with both 'http' and 'https' pointing to that
        URL. If None, no proxies will be used.
    trust_env : bool
        If True, the proxies will be read from ENV VARs (case insensitive):
            HTTP_PROXY/HTTPS_PROXY.
        NOTE: It is ignored if 'proxies' is NOT None.

    Returns
    -------
    dict
        A dictionary with proxies, either set from 'proxies' or read from ENV VARs.
    """

    if proxies is not None:
        if isinstance(proxies, str):
            return {
                "http": proxies,
                "https": proxies,
            }
        if isinstance(proxies, dict):
            return proxies
        raise TypeError(
            "If 'proxies' is not None, it must be of type dict or str. "
            f"Given type: {type(proxies)}."
        )

    if not trust_env:
        return {}

    http_proxy = (os.environ.get("HTTP_PROXY"), os.environ.get("http_proxy"))
    https_proxy = (os.environ.get("HTTPS_PROXY"), os.environ.get("https_proxy"))

    if not any(http_proxy + https_proxy):
        return {}

    proxies = {}
    if any(http_proxy):
        proxies["http"] = http_proxy[0] if http_proxy[0] else http_proxy[1]
    if any(https_proxy):
        proxies["https"] = https_proxy[0] if https_proxy[0] else https_proxy[1]

    return proxies


def _get_epoch_time() -> int:
    """
    Get the current epoch time as an integer.

    Returns
    -------
    int
        Current epoch time.
    """

    dts = datetime.datetime.utcnow()
    return round(time.mktime(dts.timetuple()) + dts.microsecond / 1e6)
