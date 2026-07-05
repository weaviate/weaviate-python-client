import pytest

from weaviate.util import _get_valid_timeout_config


class TestGetValidTimeoutConfig:
    """Validation for the client's ``timeout_config`` argument."""

    def test_single_int_expands_to_pair(self):
        assert _get_valid_timeout_config(5) == (5, 5)

    def test_single_float_expands_to_pair(self):
        assert _get_valid_timeout_config(2.5) == (2.5, 2.5)

    def test_valid_tuple_returned_unchanged(self):
        assert _get_valid_timeout_config((2, 3)) == (2, 3)

    @pytest.mark.parametrize("value", [0, -1, -0.5])
    def test_non_positive_number_raises_value_error(self, value):
        with pytest.raises(ValueError):
            _get_valid_timeout_config(value)

    @pytest.mark.parametrize("value", [(1,), (1, 2, 3)])
    def test_wrong_length_tuple_raises_value_error(self, value):
        with pytest.raises(ValueError):
            _get_valid_timeout_config(value)

    @pytest.mark.parametrize("value", [(1, -2), (-1, 2)])
    def test_non_positive_in_tuple_raises_value_error(self, value):
        with pytest.raises(ValueError):
            _get_valid_timeout_config(value)

    @pytest.mark.parametrize("value", [None, "abc", True])
    def test_non_number_raises_type_error(self, value):
        with pytest.raises(TypeError):
            _get_valid_timeout_config(value)

    @pytest.mark.parametrize("value", [("a", 2), (True, False)])
    def test_non_number_in_tuple_raises_type_error(self, value):
        with pytest.raises(TypeError):
            _get_valid_timeout_config(value)
