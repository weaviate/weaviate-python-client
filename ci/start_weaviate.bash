#!/bin/bash

echo "Download the Weaviate docker-compose file"
curl -s -o docker-compose.yml https://configuration.semi.technology/docker-compose
echo "Run Docker compose"
nohup docker-compose up &

echo "Wait until weaviate is up"

# pulling all images usually takes < 3 min
# starting weaviate usuall takes < 2 min
i="0"
curl localhost:8080/v1/meta
while [ $? -ne 0 ]; do
  i=$[$i+10]
  echo "Sleep $i"
  sleep 10
  if [ $i -gt 300 ]; then
    echo "Weaviate did not start in time"
    cat nohup.out
    exit 1
  fi
  curl localhost:8080/v1/meta
done
echo "Weaviate is up and running"
