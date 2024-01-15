import datetime
import uuid
import pytest

from weaviate.collections.classes.filters import Filter, FilterMetadata


NOW = datetime.datetime.now()


def test_old_filters_warning() -> None:
    # can't parametrize this, because the warning needs to be raised in the test and not in the parametrize
    with pytest.warns(DeprecationWarning):
        Filter("name").equal(val="thing")

    with pytest.warns(DeprecationWarning):
        FilterMetadata.ById.equal(uuid.uuid4())
    with pytest.warns(DeprecationWarning):
        FilterMetadata.ById.contains_any([uuid.uuid4()])
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ById.not_equal(uuid.uuid4())

    # creation and update time use the same underlying functions, so only test one
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ByCreationTime.not_equal(NOW)
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ByCreationTime.equal(NOW)
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ByCreationTime.less_or_equal(NOW)
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ByCreationTime.less_than(NOW)
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ByCreationTime.greater_or_equal(NOW)
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ByCreationTime.greater_than(NOW)
    with pytest.warns(expected_warning=DeprecationWarning):
        FilterMetadata.ByCreationTime.contains_any([NOW])
