import pytest

from weaviate.util import _ServerVersion


@pytest.mark.parametrize(
    "version_string,expected",
    [
        ("1.2.3.a", _ServerVersion(1, 2, 3)),
        ("1.2.3.4", _ServerVersion(1, 2, 3)),
        ("v1.2.3.4", _ServerVersion(1, 2, 3)),
        ("1.2.3", _ServerVersion(1, 2, 3)),
        ("v1.2.3", _ServerVersion(1, 2, 3)),
        ("1.2", _ServerVersion(1, 2, 0)),
        ("v1.2", _ServerVersion(1, 2, 0)),
        ("1", _ServerVersion(1, 0, 0)),
        ("v1", _ServerVersion(1, 0, 0)),
        ("", _ServerVersion(0, 0, 0)),
    ],
)
def test_server_version_successful_parsing(version_string: str, expected: _ServerVersion) -> None:
    assert _ServerVersion.from_string(version_string) == expected


@pytest.mark.parametrize(
    "version_string",
    [
        "v",
        "1.v2.3",
        "1.2.b3",
    ],
)
def test_server_version_unsuccessful_parsing(version_string: str) -> None:
    with pytest.raises(ValueError):
        _ServerVersion.from_string(version_string)


@pytest.mark.parametrize(
    "is_valid",
    [
        _ServerVersion(1, 2, 3).is_at_least(1, 2, 3),
        _ServerVersion(1, 2, 3).is_at_least(1, 2, 2),
        _ServerVersion(1, 2, 3).is_at_least(1, 1, 3),
        _ServerVersion(1, 2, 3).is_at_least(1, 1, 2),
        _ServerVersion(1, 2, 3).is_at_least(0, 2, 3),
        _ServerVersion(1, 2, 3).is_at_least(0, 2, 2),
        _ServerVersion(1, 2, 3).is_at_least(0, 1, 3),
        _ServerVersion(1, 2, 3).is_at_least(0, 1, 2),
        not _ServerVersion(1, 2, 3).is_at_least(1, 2, 4),
        not _ServerVersion(1, 2, 3).is_at_least(1, 3, 3),
        not _ServerVersion(1, 2, 3).is_at_least(1, 3, 4),
        not _ServerVersion(1, 2, 3).is_at_least(2, 2, 3),
        not _ServerVersion(1, 2, 3).is_at_least(2, 2, 4),
        not _ServerVersion(1, 2, 3).is_at_least(2, 3, 3),
        not _ServerVersion(1, 2, 3).is_at_least(2, 3, 4),
        not _ServerVersion(0, 0, 0).is_at_least(0, 0, 1),
    ],
)
def test_server_version_is_at_least(is_valid: bool) -> None:
    assert is_valid


def test_server_version_magic_methods() -> None:
    # Test __eq__
    assert _ServerVersion(1, 2, 3) == _ServerVersion(1, 2, 3)
    # Test __neq__
    assert _ServerVersion(1, 2, 3) != _ServerVersion(1, 2, 2)

    # Test __lt__
    assert _ServerVersion(1, 2, 2) < _ServerVersion(1, 2, 3)
    assert _ServerVersion(1, 1, 3) < _ServerVersion(1, 2, 3)
    assert _ServerVersion(0, 2, 3) < _ServerVersion(1, 2, 3)

    # Test __le__
    assert _ServerVersion(1, 2, 3) <= _ServerVersion(1, 2, 3)
    assert _ServerVersion(1, 2, 2) <= _ServerVersion(1, 2, 3)
    assert _ServerVersion(1, 1, 3) <= _ServerVersion(1, 2, 3)
    assert _ServerVersion(0, 2, 3) <= _ServerVersion(1, 2, 3)

    # Test __gt__
    assert _ServerVersion(1, 2, 4) > _ServerVersion(1, 2, 3)
    assert _ServerVersion(1, 3, 3) > _ServerVersion(1, 2, 3)
    assert _ServerVersion(2, 2, 3) > _ServerVersion(1, 2, 3)

    # Test __ge__
    assert _ServerVersion(1, 2, 3) >= _ServerVersion(1, 2, 3)
    assert _ServerVersion(1, 2, 4) >= _ServerVersion(1, 2, 3)
    assert _ServerVersion(1, 3, 3) >= _ServerVersion(1, 2, 3)
    assert _ServerVersion(2, 2, 3) >= _ServerVersion(1, 2, 3)
