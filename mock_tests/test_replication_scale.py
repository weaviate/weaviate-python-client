"""Proposed HTTP-contract tests for replication scale plans, for discussion.

These placeholders describe tests; they do not implement fixtures or assertions.
Exercise public client methods against mock HTTP responses, not mocked methods.
Run request/response and error scenarios with both sync and async clients. Run
input-validation and version-boundary matrices with the sync client only. Unless
a test says otherwise, mock a supported server version.
"""


def test_generate_scale_plan_request_and_parsing() -> None:
    """Send the expected GET and parse a typed, multi-shard plan.

    Call generate_scale_plan(collection="articleArchive", replication_factor=3).
    Expect GET /v1/replication/scale with query parameters collection=ArticleArchive
    and replicationFactor=3. This one name checks first-letter capitalization
    while preserving the rest of the name.

    Return plan JSON containing multiple shards with additions and removals.
    Expect a ReplicationScalePlan with a UUID plan_id, the returned collection,
    and ShardScaleActions for every shard. Each addNodes entry becomes a
    ReplicaAddition with target_node from the key and source_node from the value,
    in response order.

    Make one shard removal-only in the server's actual shape,
    {"removeNodes": ["node2"]} with no addNodes key, and expect
    remove_nodes=["node2"] and add_nodes=[] for it.
    """
    raise NotImplementedError("Test not implemented")


def test_apply_scale_plan_serialization_and_result_parsing() -> None:
    """Serialize the supplied plan and parse the application result.

    Construct a ReplicationScalePlan directly with collection="article" and call
    apply_scale_plan. Expect POST /v1/replication/scale with literal JSON matching
    the plan: planId, collection, shardScaleActions, removeNodes, and addNodes.
    The collection is sent as given ("article"); unlike generate_scale_plan,
    application does not capitalize it. Each ReplicaAddition must serialize as an
    addNodes entry keyed by target_node. Include empty removals and both named
    and None sources; None must serialize as JSON null. Include one removal-only
    shard with add_nodes=[], which must serialize with "addNodes": {} so every
    shard sends both keys.

    Return planId, collection, and multiple operationIds. Expect a
    ReplicationScaleApplyResult with UUID plan_id and operation_ids.
    """
    raise NotImplementedError("Test not implemented")


def test_apply_scale_plan_rejects_duplicate_target_nodes() -> None:
    """Reject a shard that adds two replicas on one target before sending a request.

    addNodes is a JSON object keyed by target node, so a duplicate target_node
    cannot be represented and would otherwise drop one addition silently. Call
    apply_scale_plan with a shard containing two ReplicaAddition entries for
    target_node="node3" with different sources. Expect WeaviateInvalidInputError
    identifying the shard and target node, and assert no request occurred.

    Only duplicates within one shard are invalid; the same target_node in
    different shards is valid.
    """
    raise NotImplementedError("Test not implemented")


def test_scale_methods_enforce_minimum_versions() -> None:
    """Enforce the scale-plan version minimums for generation and application.

    Call both generate_scale_plan and apply_scale_plan against each unsupported
    patch and its first supported patch:
        1.31.19 rejected; 1.31.20 accepted.
        1.32.16 rejected; 1.32.17 accepted.
        1.33.4 rejected; 1.33.5 accepted.
        1.34.0 rejected; 1.34.1 accepted.

    Rejected versions must raise WeaviateUnsupportedFeatureError identifying the
    server version and the four minimum versions, without sending an HTTP request.
    Accepted versions must send the request and return the parsed result from a
    valid mocked GET or POST response.

    These cases verify the feature's minimum-version configuration for both
    methods: a rejected case fails if a minimum is too low or if a plain
    is_at_least check replaces is_at_least_any, and an accepted case fails if a
    minimum is too high. Later patches and minors are covered by the shared
    version helper's tests.
    """
    raise NotImplementedError("Test not implemented")


def test_generate_scale_plan_raises_for_missing_collection() -> None:
    """Raise on the server's collection-not-found response instead of returning None.

    Return HTTP 404 with an empty body for GET /v1/replication/scale, matching the
    server's response for a missing collection. Expect UnexpectedStatusCodeError
    with status 404. Replication operation get treats 404 as None; generation
    must not, so a missing collection cannot pass silently as an empty result.

    Other error statuses use the shared status handling covered by
    mock_tests/test_collection.py and are not repeated here.
    """
    raise NotImplementedError("Test not implemented")
