#!/usr/bin/env bash

set -eou pipefail

export WEAVIATE_VERSION=$1

source ./ci/compose.sh

echo "Stop existing session if running"
docker compose -f ci/docker-compose-async.yml down --remove-orphans
rm -rf weaviate-data || true

echo "Run Docker compose"
docker compose -f ci/docker-compose-async.yml up -d

echo "Wait until the container is up"

wait "http://localhost:8090"

echo "All containers running"
