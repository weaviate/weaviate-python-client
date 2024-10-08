#!/usr/bin/env bash

set -eou pipefail

export WEAVIATE_VERSION=$1

source ./ci/compose.sh

echo "Stop existing session if running"
compose_down_all
rm -rf weaviate-data || true

echo "Run Docker compose"
compose_up_all

echo "Wait until all containers are up"

function wait(){
  MAX_WAIT_SECONDS=60
  ALREADY_WAITING=0

  echo "Waiting for $1"
  while true; do
    # first check if weaviate already responds
    if ! curl -s $1 > /dev/null; then
      continue
    fi

    # endpoint available, check if it is ready
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$1/v1/.well-known/ready")

    if [ "$HTTP_STATUS" -eq 200 ]; then
      break
    else
      echo "Weaviate is not up yet. (waited for ${ALREADY_WAITING}s)"
      if [ $ALREADY_WAITING -gt $MAX_WAIT_SECONDS ]; then
        echo "Weaviate did not start up in $MAX_WAIT_SECONDS."
        exit 1
      else
        sleep 2
        let ALREADY_WAITING=$ALREADY_WAITING+2
      fi
    fi
  done

  echo "Weaviate is up and running!"
}

for port in $(all_weaviate_ports); do
  wait "http://localhost:$port"
done

echo "All containers running"
