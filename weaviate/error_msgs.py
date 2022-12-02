"""
Error/Warning messages that are reused throughout the code.
"""


FILTER_BEACON_V14_CLS_NS_W = (
    "Based on the number of '/' in the beacon it seems that the beacon is not "
    "class namespaced. Weaviate version >= 1.14.0 STRONGLY recommends using class "
    "namespaced beacons. Non-class namespaced beacons will be removed in future "
    "versions. Class namespaced beacons look like this: "
    "'weaviate://localhost/{CLASS_NAME}/{UUID}'"
)


BATCH_MANUAL_USE_W = (
    "You are manually batching this means you are NOT using the client's "
    "built-in multi-threading. Setting `batch_size` in `client.batch.configure()` "
    "to an int value will enabled this. Also see: https://weaviate.io/developers/"
    "weaviate/current/restful-api-references/batch.html#example-request-1"
)


BATCH_REF_DEPRECATION_NEW_V14_CLS_NS_W = (
    "Weaviate Server version >= 1.14.x STRONGLY recommends using class namespaced "
    "beacons, please specify the `to_object_class_name` argument for this. The "
    "non-class namespaced beacons (None value for `to_object_class_name`) are going "
    "to be removed in the future versions of the Weaviate Server and Weaviate Python "
    "Client."
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
    "APIs, please specify the `class_name` argument for this. The non-class "
    "namespaced APIs (None value for `class_name`) are going to be removed in the "
    "future versions of the Weaviate Server and Weaviate Python Client."
)


DATA_DEPRECATION_OLD_V14_CLS_NS_W = (
    "Weaviate Server version < 1.14.x does not support class namespaced APIs. The "
    "non-class namespaced APIs calls are going to be made instead (None value for "
    "`class_name`). The non-class namespaced APIs are going to be removed in "
    "future versions of the Weaviate Server and Weaviate Python Client. "
    "Please upgrade your Weaviate Server version."
)


REF_DEPRECATION_NEW_V14_CLS_NS_W = (  # del
    "Weaviate Server version >= 1.14.x STRONGLY recommends using class namespaced "
    "APIs and beacons, please set the `from_class_name` AND `to_class_name` arguments "
    "for this. The non-class namespaced APIs and beacons (None value for "
    "`from_class_name` AND `to_class_name`) are going to be removed in future "
    "versions of the Weaviate Server and Weaviate Python Client."
)


REF_DEPRECATION_OLD_V14_FROM_CLS_NS_W = (
    "Weaviate Server version < 1.14.x does not support class namespaced APIs. "
    "The non-class namespaced APIs calls are going to be made instead "
    "(None value for `from_class_name`). The non-class namespaced APIs and "
    "beacons are going to be removed in future versions of the Weaviate Server "
    "and Weaviate Python Client. Please upgrade your Weaviate Server version."
)


REF_DEPRECATION_OLD_V14_TO_CLS_NS_W = (
    "Weaviate Server version < 1.14.x does not support class namespaced beacons. "
    "The non-class namespaced beacons are going to be constructed instead "
    "(None value for `to_class_name`). The non-class namespaced APIs and "
    "beacons are going to be removed in future versions of the Weaviate Server "
    "and Weaviate Python Client. Please upgrade your Weaviate Server version."
)


BATCH_EXECUTOR_SHUTDOWN_W = (
    "The BatchExecutor was shutdown, most probably when it exited the `with` statement. "
    "It will be initialized again. If you are not `batch` in the `with client.batch as batch` "
    "please make sure to shut it down when done importing data: `client.batch.shutdown()`. "
    "You can start it again using the `client.batch.start()` method."
)
