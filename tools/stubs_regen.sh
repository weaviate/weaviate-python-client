#!/bin/bash

echo "Regenerating stubs..."

python3 -m tools.stubs
black ./weaviate

echo "done"