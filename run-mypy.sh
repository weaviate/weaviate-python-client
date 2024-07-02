#!/usr/bin/env bash

python3 -m venv venv
source venv/bin/activate
pip install -r requirements-devel.txt >/dev/null 2>&1

mypy --config-file ./pyproject.toml --warn-unused-ignores ./weaviate