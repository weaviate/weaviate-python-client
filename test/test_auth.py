import pytest
import weaviate.classes as wvc


@pytest.mark.parametrize("expires_in,warning", [(-1, True), (5, False)])
def test_bearer_validation(
    recwarn: pytest.WarningsRecorder, expires_in: int, warning: bool
) -> None:
    wvc.init.Auth.bearer_token(
        access_token="Doesn't matter",
        refresh_token="Doesn't matter",
        expires_in=expires_in,
    )

    if warning:
        assert len(recwarn) == 1
        w = recwarn.pop()
        assert issubclass(w.category, UserWarning)
        assert str(w.message).startswith("Auth003")
    else:
        assert len(recwarn) == 0
