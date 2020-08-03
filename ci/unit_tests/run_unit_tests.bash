#!/bin/bash

function runTest {
    echo "Testing: $1"
    python -m unittest "$1"
}



# /test
runTest "test.add_action_batch"
runTest "test.add_reference"
runTest "test.add_reference_batch"
runTest "test.add_thing"
runTest "test.add_thing_batch"
runTest "test.auth"
runTest "test.c11y"
runTest "test.classification"
runTest "test.client"
runTest "test.read_delete_entity"
runTest "test.exceptions"
runTest "test.is_reachable"
runTest "test.patch_entity"
runTest "test.query"
runTest "test.schema"
runTest "test.util"
runTest "test.validate_schema"

# /test/tools
runTest "test.tools.batcher"