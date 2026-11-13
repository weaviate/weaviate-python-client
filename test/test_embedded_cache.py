import hashlib
import io
import tarfile
import zipfile
from pathlib import Path
from typing import List

import httpx
import pytest

from weaviate import embedded


def _instance(version: str, root: Path) -> embedded.EmbeddedV4:
    return embedded.EmbeddedV4(
        embedded.EmbeddedOptions(
            version=version,
            binary_path=str(root / "bin"),
            persistence_data_path=str(root / "data"),
        )
    )


@pytest.fixture
def downloads(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    downloaded: List[str] = []
    monkeypatch.setattr(embedded.platform, "system", lambda: "Linux")

    def retrieve(url: str, filename: Path) -> None:
        downloaded.append(url)
        payload = url.encode("utf-8")
        if url.endswith(".zip"):
            with zipfile.ZipFile(filename, "w") as archive:
                archive.writestr("weaviate", payload)
        else:
            with tarfile.open(filename, "w:gz") as archive:
                member = tarfile.TarInfo("weaviate")
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))

    monkeypatch.setattr(embedded.urllib.request, "urlretrieve", retrieve)
    return downloaded


@pytest.mark.parametrize("extension", ["tar.gz", "zip"])
@pytest.mark.parametrize("different_host", [False, True])
def test_custom_urls_select_their_own_binary(
    tmp_path: Path, downloads: List[str], extension: str, different_host: bool
) -> None:
    urls = [
        f"https://downloads.example.org/build-a/weaviate.{extension}",
        (
            f"https://mirror.example.org/build-a/weaviate.{extension}"
            if different_host
            else f"https://downloads.example.org/build-b/weaviate.{extension}"
        ),
    ]
    selected = []
    for url in urls:
        instance = _instance(url, tmp_path)
        instance.ensure_weaviate_binary_exists()
        selected.append(instance._weaviate_binary_path.read_bytes())

    assert selected == [url.encode("utf-8") for url in urls]
    assert downloads == urls


@pytest.mark.parametrize("extension", ["tar.gz", "zip"])
def test_repeated_custom_url_reuses_its_binary(
    tmp_path: Path, downloads: List[str], extension: str
) -> None:
    url = f"https://downloads.example.org/build-a/weaviate.{extension}"
    for _ in range(2):
        instance = _instance(url, tmp_path)
        instance.ensure_weaviate_binary_exists()
        assert instance._weaviate_binary_path.read_bytes() == url.encode("utf-8")

    assert downloads == [url]


@pytest.mark.parametrize("extension", ["tar.gz", "zip"])
def test_custom_url_does_not_reuse_anonymous_legacy_binary(
    tmp_path: Path, downloads: List[str], extension: str
) -> None:
    url = f"https://downloads.example.org/build-a/weaviate.{extension}"
    instance = _instance(url, tmp_path)
    legacy = tmp_path / "bin" / f"weaviate--{hashlib.sha256(b'').hexdigest()}"
    legacy.write_bytes(b"a different custom build")

    instance.ensure_weaviate_binary_exists()

    assert instance._weaviate_binary_path.read_bytes() == url.encode("utf-8")
    assert downloads == [url]
    assert legacy.read_bytes() == b"a different custom build"


@pytest.mark.parametrize(
    "version",
    [
        "1.39.7",
        "https://github.com/weaviate/weaviate/releases/download/v1.39.7/weaviate-v1.39.7-linux-amd64.tar.gz",
        "latest",
    ],
)
def test_known_version_reuses_existing_cache(
    tmp_path: Path, downloads: List[str], monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    monkeypatch.setattr(
        embedded.httpx, "get", lambda url: httpx.Response(200, json={"tag_name": "v1.39.7"})
    )
    instance = _instance(version, tmp_path)
    cached = tmp_path / "bin" / f"weaviate-v1.39.7-{hashlib.sha256(b'v1.39.7').hexdigest()}"
    cached.write_bytes(b"the cached official version")

    instance.ensure_weaviate_binary_exists()

    assert instance._weaviate_binary_path == cached
    assert instance._weaviate_binary_path.read_bytes() == b"the cached official version"
    assert downloads == []


def test_latest_resolves_current_version_before_reusing_cache(
    tmp_path: Path, downloads: List[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    tags = iter(["v1.39.7", "v1.40.0"])
    monkeypatch.setattr(
        embedded.httpx, "get", lambda url: httpx.Response(200, json={"tag_name": next(tags)})
    )
    (tmp_path / "bin").mkdir()
    for tag in ["v1.39.7", "v1.40.0"]:
        cached = tmp_path / "bin" / f"weaviate-{tag}-{hashlib.sha256(tag.encode()).hexdigest()}"
        cached.write_bytes(tag.encode())

    for expected in [b"v1.39.7", b"v1.40.0"]:
        instance = _instance("latest", tmp_path)
        instance.ensure_weaviate_binary_exists()
        assert instance._weaviate_binary_path.read_bytes() == expected

    assert downloads == []
