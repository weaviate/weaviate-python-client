#!/bin/bash

echo "Run Docker compose"
nohup docker-compose -f ci/docker-compose.yml up -d

echo "Wait until weaviate is up"

# pulling all images usually takes < 3 min
# starting weaviate usuall takes < 2 min
i="0"
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" localhost:8080/v1/.well-known/ready)

while [ $STATUS_CODE -ne 200 ]; do
  i=$[$i+5]
  echo "Sleep $i"
  sleep 5
  if [ $i -gt 300 ]; then
    echo "Weaviate did not start in time"
    cat nohup.out
    exit 1
  fi
  STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" localhost:8080/v1/.well-known/ready)
done
echo "Weaviate is up and running"
