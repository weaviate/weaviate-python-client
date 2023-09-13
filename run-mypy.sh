#!/usr/bin/env bash

set -o errexist

pip install -r requirements-devel.txt

mypy --config-file ./pyproject.toml ./weaviate