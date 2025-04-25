#!/bin/bash

echo "Regenerating stubs..."

python3 -m tools.stubs
ruff check ./weaviate --select F401 --select I --fix
ruff format ./weaviate

echo "done"