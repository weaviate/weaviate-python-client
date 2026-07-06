import pytest

from weaviate.util import parse_version_string


class TestParseVersionString:
    """`parse_version_string` -> (major, minor), ignoring any patch."""

    @pytest.mark.parametrize(
        "version,expected",
        [
            ("1.18.1", (1, 18)),
            ("1.18", (1, 18)),
            ("1.0.0", (1, 0)),
        ],
    )
    def test_major_minor_parsed_and_patch_ignored(self, version, expected):
        assert parse_version_string(version) == expected

    @pytest.mark.parametrize("version", ["v1.18.2", "v3.4"])
    def test_leading_v_is_stripped(self, version):
        assert parse_version_string(version) == parse_version_string(version[1:])

    def test_version_without_minor_defaults_to_zero(self):
        assert parse_version_string("2") == (2, 0)

    @pytest.mark.parametrize("version", ["abc", ""])
    def test_unparseable_version_raises_value_error(self, version):
        with pytest.raises(ValueError):
            parse_version_string(version)
