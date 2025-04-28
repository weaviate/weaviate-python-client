#!/bin/bash

echo "Regenerating stubs..."

python3 -m tools.stubs
ruff check ./weaviate --select F401 --select I --fix # only fix unused/sorted imports
ruff format ./weaviate

echo "done"