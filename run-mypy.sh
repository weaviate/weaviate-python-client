#!/usr/bin/env bash

pip install -r requirements-devel.txt >/dev/null 2>&1

mypy --config-file ./pyproject.toml ./weaviate