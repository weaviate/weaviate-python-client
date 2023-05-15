#!/bin/bash

echo "Run Docker compose"
nohup docker-compose -f ci/docker-compose.yml up -d
nohup docker-compose -f ci/docker-compose-azure.yml up -d
nohup docker-compose -f ci/docker-compose-okta-cc.yml up -d
nohup docker-compose -f ci/docker-compose-okta-users.yml up -d
nohup docker-compose -f ci/docker-compose-wcs.yml up -d
nohup docker-compose -f ci/docker-compose-openai.yml up -d
nohup docker-compose -f ci/docker-compose-cluster.yml up -d
