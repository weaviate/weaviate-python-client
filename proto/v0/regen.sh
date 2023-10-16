#!/bin/bash

echo "this script assumes that you have checked out weaviate next to the client"
cd "${0%/*}/.."


python3 -m grpc_tools.protoc  -I ../../weaviate/grpc/proto --python_out=./ --pyi_out=./ --grpc_python_out=./ ../../weaviate/grpc/proto/v0/*.proto


sed -i ''  's/import weaviate_pb2/from . import weaviate_pb2/g' v0/*.py
sed -i ''  's/import batch_pb2/from . import batch_pb2/g' v0/*.py
sed -i ''  's/import search_get_pb2/from . import search_get_pb2/g' v0/*.py
sed -i ''  's/import base_pb2/from . import base_pb2/g' v0/*.py

echo "done"

