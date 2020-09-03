#!/bin/bash

function runTest {
    echo "Testing: $1"
    python -m unittest "$1"
}


# /test
runTest "test.auth"
runTest "test.client"
runTest "test.exceptions"
runTest "test.is_reachable"
runTest "test.util"

# /test/batch
runTest "test.batch.add_action_batch"
runTest "test.batch.add_reference_batch"
runTest "test.batch.add_thing_batch"

# /test/classification
runTest "test.classification.classification"

# /test/connection
runTest "test.connection.test_connection"

# /test/contextionary
runTest "test.contextionary.c11y"

# /test/data
runTest "test.data.add_replace_thing"
runTest "test.data.patch_entity"
runTest "test.data.read_delete_entity"
# /test/data/references
runTest "test.data.references.add_reference"
runTest "test.data.references.delete"

# /test/gql
runTest "test.gql.builder_test"
runTest "test.gql.filter_test"
runTest "test.gql.gql_test"

# /test/schema
runTest "test.schema.test_schema"
runTest "test.schema.validate_schema"
runTest "test.schema.test_properties"

# /test/tools
runTest "test.tools.batcher_test"