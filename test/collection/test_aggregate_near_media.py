import pytest

from weaviate.collections.grpc.aggregate import _AggregateGRPC
from weaviate.util import _ServerVersion


@pytest.mark.parametrize(
    "type_,field,media_field",
    [
        ("audio", "near_audio", "audio"),
        ("depth", "near_depth", "depth"),
        ("image", "near_image", "image"),
        ("imu", "near_imu", "imu"),
        ("thermal", "near_thermal", "thermal"),
        ("video", "near_video", "video"),
    ],
)
def test_near_media_request(type_: str, field: str, media_field: str) -> None:
    grpc = _AggregateGRPC(_ServerVersion(1, 36, 0), "Dummy", "tenant1", None, True)

    request = grpc.near_media(
        media="aGVsbG8=",
        type_=type_,  # type: ignore[arg-type]
        certainty=None,
        distance=0.3,
        target_vector=None,
        aggregations=[],
        filters=None,
        group_by=None,
        limit=None,
        object_limit=5,
        objects_count=True,
    )

    assert request.WhichOneof("search") == field
    search = getattr(request, field)
    assert getattr(search, media_field) == "aGVsbG8="
    assert search.distance == pytest.approx(0.3)
    assert request.object_limit == 5
    assert request.objects_count is True
    assert request.tenant == "tenant1"
