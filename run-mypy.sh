#!/usr/bin/env bash

pip install -r requirements-devel.txt >/dev/null 2>&1

echo "Static checking ./weaviate:"
mypy --config-file ./pyproject.toml ./weaviate
echo "Static checking ./integration:"
mypy --config-file ./pyproject.toml ./integration