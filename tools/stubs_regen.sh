#!/bin/bash

echo "Regenerating stubs..."

python3 -m tools.stubs
# ruff check . --select F401 --select I --fix --exclude weaviate/proto
black ./weaviate

echo "done"