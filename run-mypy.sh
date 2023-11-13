#!/usr/bin/env bash

pip install -r requirements-devel.txt

mypy --config-file ./pyproject.toml ./weaviate