#!/usr/bin/env bash

set -eou pipefail

export WEAVIATE_VERSION=$1

docker-compose -f ci/docker-compose.yml down --remove-orphans
docker-compose -f ci/docker-compose-async.yml down --remove-orphans
docker-compose -f ci/docker-compose-azure.yml down --remove-orphans
docker-compose -f ci/docker-compose-okta-cc.yml down --remove-orphans
docker-compose -f ci/docker-compose-okta-users.yml down --remove-orphans
docker-compose -f ci/docker-compose-wcs.yml down --remove-orphans
docker-compose -f ci/docker-compose-generative.yml down --remove-orphans
docker-compose -f ci/docker-compose-cluster.yml down --remove-orphans
docker-compose -f ci/docker-compose-rerank.yml down --remove-orphans
docker-compose -f ci/docker-compose-proxy.yml down --remove-orphans