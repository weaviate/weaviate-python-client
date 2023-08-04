#!/usr/bin/env bash

ci/start_weaviate.sh
# pytest ./test
pytest $1
ci/stop_weaviate.sh