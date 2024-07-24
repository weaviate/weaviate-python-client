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