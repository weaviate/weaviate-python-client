#!/usr/bin/env bash
source ~/.bash_profile

echo "Running tests in $2"
pyenv activate wpc-pyd-exp-$2
mypy ./weaviate
pytest $1 -vv --full-trace
pyenv deactivate