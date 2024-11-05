#!/usr/bin/env bash

set -eou pipefail

function ls_compose {
  ls ci | grep 'docker-compose'
}

function exec_all {
  for file in $(ls_compose); do
    docker compose -f $(echo "ci/${file} ${1}")
  done
}

function compose_up_all {
  exec_all "up -d"
}

function compose_down_all {
  exec_all "down --remove-orphans"
}

function all_weaviate_ports {
  echo "8090 8081 8087 8088 8089 8086 8082 8083 8075 8079 8085 8080" # in alphabetic order of appearance in docker-compose files
}

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