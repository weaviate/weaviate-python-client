#!/usr/bin/env bash
source ~/.bash_profile

export OPENAI_APIKEY=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

ci/start_weaviate.sh
echo "Running tests in $2"
pyenv activate wpc-pyd-exp-$2
echo "Running specified integration tests: $1"
pytest $1 -vv
pyenv deactivate
ci/stop_weaviate.sh

