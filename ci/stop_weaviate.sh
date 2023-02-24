#!/bin/bash

docker-compose -f ci/docker-compose.yml down --remove-orphans
docker-compose -f ci/docker-compose-azure.yml down --remove-orphans
docker-compose -f ci/docker-compose-okta-cc.yml down --remove-orphans
docker-compose -f ci/docker-compose-okta-users.yml down --remove-orphans
docker-compose -f ci/docker-compose-wcs.yml down --remove-orphans
docker-compose -f ci/docker-compose_openai.yml down --remove-orphans
