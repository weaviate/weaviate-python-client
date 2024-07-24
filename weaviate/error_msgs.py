"""
Error and Warning messages that are reused throughout the code.
"""

FILTER_BEACON_V14_CLS_NS_W = (
    "Based on the number of '/' in the beacon it seems that the beacon is not "
    "class namespaced. Weaviate version >= 1.14.0 STRONGLY recommends using class "
    "namespaced beacons. Non-class namespaced beacons will be removed in future "
    "versions. Class namespaced beacons look like this: "
    "'weaviate://localhost/{CLASS_NAME}/{UUID}'"
)


BATCH_MANUAL_USE_W = (
    "Manually batching means this code is NOT using the client's built-in "
    "multi-threading. To enable built-in multi-threading, set `batch_size` in "
    " `client.batch.configure()` to an integer value . See also:"
    "https://weaviate.io/developers/weaviate/current/restful-api-references/"
)


BATCH_REF_DEPRECATION_NEW_V14_CLS_NS_W = (
    "Weaviate Server version >= 1.14.x STRONGLY recommends using class namespaced "
    "beacons. To use class namespaced beacons, specify the `to_object_class_name` "
    "argument. Non-class namespaced beacons (None value for `to_object_class_name`) "
    "will be removed in future versions of the Weaviate Server and Weaviate "
    "Python Client."
)


BATCH_REF_DEPRECATION_OLD_V14_CLS_NS_W = (
    "Weaviate Server version < 1.14.x does not support class namespaced APIs. The "
    "non-class namespaced APIs calls are going to be made instead (None value for "
    "`class_name`). The non-class namespaced APIs are going to be removed in "
    "future versions of the Weaviate Server and Weaviate Python Client. "
    "Please upgrade your Weaviate Server version."
)


DATA_DEPRECATION_NEW_V14_CLS_NS_W = (
    "Weaviate Server version >= 1.14.x STRONGLY recommends using class namespaced "
    "APIs. To use class namespaced APIs, specify the `class_name` argument. "
    "Non-class namespaced APIs (None value for `to_object_class_name`) will be "
    "removed in future versions of the Weaviate Server and Weaviate Python Client."
)


DATA_DEPRECATION_OLD_V14_CLS_NS_W = (
    "Weaviate Server version < 1.14.x does not support class namespaced APIs. "
    "Non-class namespaced APIs calls will be made instead (None value for "
    "`class_name`). Non-class namespaced APIs will be removed in future versions "
    "of the Weaviate Server and Weaviate Python Client. Please upgrade your "
    "Weaviate Server version."
)


REF_DEPRECATION_NEW_V14_CLS_NS_W = (  # del
    "Weaviate Server version >= 1.14.x STRONGLY recommends using class namespaced "
    "APIs and beacons. To use class namespaced APIs and beacons, specify, the "
    "`from_class_name` AND `to_class_name` arguments. Non-class namespaced APIs "
    "and beacons (None value for `from_class_name` AND `to_class_name`) will be "
    "removed in future versions of the Weaviate Server and Weaviate Python Client."
)


REF_DEPRECATION_OLD_V14_FROM_CLS_NS_W = (
    "Weaviate Server version < 1.14.x does not support class namespaced APIs. "
    "Non-class namespaced APIs calls will to be made instead (None value for "
    "`from_class_name`). Non-class namespaced APIs and  beacons will be removed "
    "in future versions of the Weaviate Server and Weaviate Python Client. Please "
    "upgrade your Weaviate Server version."
)


REF_DEPRECATION_OLD_V14_TO_CLS_NS_W = (
    "Weaviate Server version < 1.14.x does not support class namespaced beacons. "
    "Non-class namespaced beacons will be constructed instead (None value for "
    "`to_class_name`). Non-class namespaced APIs and beacons will be removed in "
    "future versions of the Weaviate Server and Weaviate Python Client. Please "
    "upgrade your Weaviate Server version."
)


BATCH_EXECUTOR_SHUTDOWN_W = (
    "The BatchExecutor was shutdown, most probably when it exited the `with` statement. "
    "The BatchExecutor will be reinitialized. If you are not `batch` in "
    "`with client.batch as batch`, be sure to shut the BatchExecutor down when "
    "your data import finishes: `client.batch.shutdown()`. To restart the "
    "BatchExecutor, use `client.batch.start()`."
)
