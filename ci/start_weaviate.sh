#!/usr/bin/env bash

set -eou pipefail

export WEAVIATE_VERSION=$1

echo "Run Docker compose"
nohup docker-compose -f ci/docker-compose.yml up -d
nohup docker-compose -f ci/docker-compose-async.yml up -d
nohup docker-compose -f ci/docker-compose-azure.yml up -d
nohup docker-compose -f ci/docker-compose-okta-cc.yml up -d
nohup docker-compose -f ci/docker-compose-okta-users.yml up -d
nohup docker-compose -f ci/docker-compose-wcs.yml up -d
nohup docker-compose -f ci/docker-compose-generative.yml up -d
nohup docker-compose -f ci/docker-compose-cluster.yml up -d
nohup docker-compose -f ci/docker-compose-rerank.yml up -d
nohup docker-compose -f ci/docker-compose-proxy.yml up -d