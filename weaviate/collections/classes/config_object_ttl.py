import datetime
from typing import Optional

from weaviate.collections.classes.config_base import _ConfigCreateModel


class _ObjectTTLCreate(_ConfigCreateModel):
    enabled: bool = True
    postSearchFilter: Optional[bool]
    deleteOn: Optional[str]
    defaultTtl: Optional[int]


class _ObjectTTL:
    """Configuration class for Weaviate's object time-to-live (TTL) feature."""

    @staticmethod
    def delete_by_update_time(
        time_to_live: int | datetime.timedelta,
        post_search_filter: Optional[bool] = None,
    ) -> _ObjectTTLCreate:
        """Create an `ObjectTimeToLiveConfig` object to be used when defining the object time-to-live configuration of Weaviate.

        Args:
            time_to_live: The time-to-live for objects in seconds.
            post_search_filter: If enabled search results will be filtered to remove expired objects that have not yet been deleted.
        """
        if isinstance(time_to_live, datetime.timedelta):
            time_to_live = int(time_to_live.total_seconds())
        return _ObjectTTLCreate(
            deleteOn="_lastUpdateTimeUnix",
            postSearchFilter=post_search_filter,
            defaultTtl=time_to_live,
        )

    @staticmethod
    def delete_by_creation_time(
        time_to_live: int | datetime.timedelta,
        post_search_filter: Optional[bool] = None,
    ) -> _ObjectTTLCreate:
        """Create an `ObjectTimeToLiveConfig` object to be used when defining the object time-to-live configuration of Weaviate.

        Args:
            time_to_live: The time-to-live for objects in seconds. Must be a positive value.
            post_search_filter: If enabled search results will be filtered to remove expired objects that have not yet been deleted.
        """
        if isinstance(time_to_live, datetime.timedelta):
            time_to_live = int(time_to_live.total_seconds())
        return _ObjectTTLCreate(
            deleteOn="_creationTimeUnix",
            postSearchFilter=post_search_filter,
            defaultTtl=time_to_live,
        )

    @staticmethod
    def delete_by_date_property(
        date_property: str,
        time_to_live_after_date: Optional[int | datetime.timedelta] = None,
        post_search_filter: Optional[bool] = None,
    ) -> _ObjectTTLCreate:
        """Create an Object ttl config for a custom date property.

        Args:
            date_property: The name of the date property to use for object expiration.
            time_to_live_after_date: The time-to-live for objects in seconds after the date property value. Can be negative
            post_search_filter: If enabled search results will be filtered to remove expired objects that have not yet been deleted.
        """
        if isinstance(time_to_live_after_date, datetime.timedelta):
            time_to_live_after_date = int(time_to_live_after_date.total_seconds())
        if time_to_live_after_date is None:
            time_to_live_after_date = 0
        return _ObjectTTLCreate(
            deleteOn=date_property,
            postSearchFilter=post_search_filter,
            defaultTtl=time_to_live_after_date,
        )
