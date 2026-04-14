from typing import Any, List, Tuple
from unittest.mock import MagicMock

import grpc
import pytest

from weaviate.config import GrpcConfig
from weaviate.connect import base as base_module
from weaviate.connect.base import ConnectionParams, ProtocolParams


@pytest.fixture
def secure_params() -> ConnectionParams:
    return ConnectionParams(
        http=ProtocolParams(host="localhost", port=8080, secure=False),
        grpc=ProtocolParams(host="localhost", port=50051, secure=True),
    )


@pytest.fixture
def insecure_params() -> ConnectionParams:
    return ConnectionParams(
        http=ProtocolParams(host="localhost", port=8080, secure=False),
        grpc=ProtocolParams(host="localhost", port=50051, secure=False),
    )


@pytest.fixture
def mock_grpc(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.aio = MagicMock()
    monkeypatch.setattr(base_module, "grpc", mock)
    return mock


@pytest.fixture
def mock_ssl_creds(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(base_module, "ssl_channel_credentials", mock)
    return mock


def test_grpc_config_channel_options() -> None:
    opts: List[Tuple[str, Any]] = [("grpc.ssl_target_name_override", "my-host")]
    config = GrpcConfig(channel_options=opts)
    assert config.channel_options == opts


def test_secure_channel_default_credentials(
    secure_params: ConnectionParams, mock_grpc: MagicMock, mock_ssl_creds: MagicMock
) -> None:
    mock_channel = MagicMock()
    mock_grpc.secure_channel.return_value = mock_channel

    result = secure_params._grpc_channel(proxies={}, grpc_msg_size=None, is_async=False)

    mock_ssl_creds.assert_called_once_with()
    mock_grpc.secure_channel.assert_called_once()
    assert result is mock_channel


def test_insecure_channel_no_config(
    insecure_params: ConnectionParams, mock_grpc: MagicMock
) -> None:
    mock_channel = MagicMock()
    mock_grpc.insecure_channel.return_value = mock_channel

    result = insecure_params._grpc_channel(proxies={}, grpc_msg_size=None, is_async=False)

    mock_grpc.insecure_channel.assert_called_once()
    assert result is mock_channel


def test_channel_options_appended_secure(
    secure_params: ConnectionParams, mock_grpc: MagicMock, mock_ssl_creds: MagicMock
) -> None:
    config = GrpcConfig(
        channel_options=[("grpc.ssl_target_name_override", "my-gateway.example.com")]
    )
    secure_params._grpc_channel(proxies={}, grpc_msg_size=None, is_async=False, grpc_config=config)

    options = mock_grpc.secure_channel.call_args.kwargs["options"]
    assert ("grpc.ssl_target_name_override", "my-gateway.example.com") in options


def test_channel_options_appended_insecure(
    insecure_params: ConnectionParams, mock_grpc: MagicMock
) -> None:
    config = GrpcConfig(channel_options=[("grpc.keepalive_time_ms", 30000)])
    insecure_params._grpc_channel(
        proxies={}, grpc_msg_size=None, is_async=False, grpc_config=config
    )

    options = mock_grpc.insecure_channel.call_args.kwargs["options"]
    assert ("grpc.keepalive_time_ms", 30000) in options


def test_credentials(
    secure_params: ConnectionParams, mock_grpc: MagicMock, mock_ssl_creds: MagicMock
) -> None:
    creds = grpc.ssl_channel_credentials()
    config = GrpcConfig(credentials=creds)
    secure_params._grpc_channel(proxies={}, grpc_msg_size=None, is_async=False, grpc_config=config)

    mock_ssl_creds.assert_not_called()
    assert mock_grpc.secure_channel.call_args.kwargs["credentials"] is creds
