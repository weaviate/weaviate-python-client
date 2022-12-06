import pytest

from weaviate import AuthBearerToken


@pytest.mark.parametrize(
    "expires_in,refresh_expires_in, warning",
    [(-1, 5, True), (1, -5, True), (-9, -5, True), (5, 10, False)],
)
def test_bearer_validation(recwarn, expires_in: int, refresh_expires_in: int, warning: bool):
    AuthBearerToken(
        access_token="Doesn't matter",
        refresh_token="Doesn't matter",
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in,
    )

    if warning:
        assert len(recwarn) == 1
        w = recwarn.pop()
        assert issubclass(w.category, UserWarning)
        assert str(w.message).startswith("Auth003")
    else:
        assert len(recwarn) == 0
