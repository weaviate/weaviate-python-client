import datetime
from typing import Optional

from weaviate.collections.classes.config_base import _ConfigCreateModel


class _ObjectTTLCreate(_ConfigCreateModel):
    enabled: bool = True
    filterExpiredObjects: Optional[bool]
    deleteOn: Optional[str]
    defaultTtl: Optional[int]


class _ObjectTTL:
    """Configuration class for Weaviate's object time-to-live (TTL) feature."""

    @staticmethod
    def delete_by_update_time(
        time_to_live: int | datetime.timedelta,
        filter_expired_objects: Optional[bool] = None,
    ) -> _ObjectTTLCreate:
        """Create an `ObjectTimeToLiveConfig` object to be used when defining the object time-to-live configuration of Weaviate.

        Args:
            time_to_live: The time-to-live for objects in relation to their last update time (seconds). Must be positive.
            filter_expired_objects: If enabled, exclude expired but not deleted objects from search results.
        """
        if isinstance(time_to_live, datetime.timedelta):
            time_to_live = int(time_to_live.total_seconds())
        return _ObjectTTLCreate(
            deleteOn="_lastUpdateTimeUnix",
            filterExpiredObjects=filter_expired_objects,
            defaultTtl=time_to_live,
        )

    @staticmethod
    def delete_by_creation_time(
        time_to_live: int | datetime.timedelta,
        filter_expired_objects: Optional[bool] = None,
    ) -> _ObjectTTLCreate:
        """Create an `ObjectTimeToLiveConfig` object to be used when defining the object time-to-live configuration of Weaviate.

        Args:
            time_to_live: The time-to-live for objects in relation to their creation time (seconds). Must be positive.
            filter_expired_objects: If enabled, exclude expired but not deleted objects from search results.
        """
        if isinstance(time_to_live, datetime.timedelta):
            time_to_live = int(time_to_live.total_seconds())
        return _ObjectTTLCreate(
            deleteOn="_creationTimeUnix",
            filterExpiredObjects=filter_expired_objects,
            defaultTtl=time_to_live,
        )

    @staticmethod
    def delete_by_date_property(
        property_name: str,
        ttl_offset: Optional[int | datetime.timedelta] = None,
        filter_expired_objects: Optional[bool] = None,
    ) -> _ObjectTTLCreate:
        """Create an Object ttl config for a custom date property.

        Args:
            property_name: The name of the date property to use for object expiration.
            ttl_offset: The time-to-live for objects relative to the date (seconds if integer). Can be negative for indicating that objects should expire before the date property value.
            filter_expired_objects: If enabled, exclude expired but not deleted objects from search results.
        """
        if isinstance(ttl_offset, datetime.timedelta):
            ttl_offset = int(ttl_offset.total_seconds())
        if ttl_offset is None:
            ttl_offset = 0
        return _ObjectTTLCreate(
            deleteOn=property_name,
            filterExpiredObjects=filter_expired_objects,
            defaultTtl=ttl_offset,
        )
