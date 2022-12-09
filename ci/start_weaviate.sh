#!/bin/bash

echo "Run Docker compose"
nohup docker-compose -f ci/docker-compose.yml up -d
nohup docker-compose -f ci/docker-compose-azure.yml up -d
nohup docker-compose -f ci/docker-compose-okta-cc.yml up -d
nohup docker-compose -f ci/docker-compose-okta-users.yml up -d
nohup docker-compose -f ci/docker-compose-wcs.yml up -d

echo "Wait until weaviate is up"

for port in 8080 8081 8082 8083 8085
do
  # pulling all images usually takes < 3 min
  # starting weaviate usually takes < 2 min
  i="0"
  STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" localhost:"$port"/v1/.well-known/ready)

  while [ "$STATUS_CODE" -ne 200 ]; do
    i=$(($i+5))
    echo "Sleep $i"
    sleep 5
    if [ $i -gt 150 ]; then
      echo "Weaviate did not start in time"
      bash ./ci/stop_weaviate.sh
      exit 1
    fi
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" localhost:"$port"/v1/.well-known/ready)
  done
  echo "Weaviate on port $port is up and running"
done