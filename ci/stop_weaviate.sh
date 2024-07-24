#!/usr/bin/env bash

set -eou pipefail

export WEAVIATE_VERSION=$1

source ./ci/compose.sh

compose_down_all
rm -rf weaviate-data || true