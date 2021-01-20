#!/bin/bash

echo "Download the Weaviate docker-compose file"
curl -s -o docker-compose.yaml "https://configuration.semi.technology/docker-compose?"
echo "Run Docker compose"
nohup docker-compose up -d

echo "Wait until weaviate is up"

# pulling all images usually takes < 3 min
# starting weaviate usuall takes < 2 min
i="0"
curl -s localhost:8080/v1/meta
while [ $? -ne 0 ]; do
  i=$[$i+5]
  echo "Sleep $i"
  sleep 5
  if [ $i -gt 300 ]; then
    echo "Weaviate did not start in time"
    cat nohup.out
    exit 1
  fi
  curl -s localhost:8080/v1/meta
done
echo "Weaviate is up and running"
