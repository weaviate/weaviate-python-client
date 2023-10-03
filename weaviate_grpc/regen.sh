#!/bin/bash

echo "this script assumes that you have checked out weaviate next to the client"
cd "${0%/*}/.."


python3 -m grpc_tools.protoc  -I ../weaviate/grpc/proto --python_out=./weaviate_grpc --pyi_out=./weaviate_grpc --grpc_python_out=./weaviate_grpc ../weaviate/grpc/proto/*.proto


sed -i ''  's/import weaviate_pb2/from . import weaviate_pb2/g' weaviate_grpc/*.py
sed -i ''  's/import batch_pb2/from . import batch_pb2/g' weaviate_grpc/*.py
sed -i ''  's/import search_get_pb2/from . import search_get_pb2/g' weaviate_grpc/*.py
sed -i ''  's/import search_get_v1_pb2/from . import search_get_v1_pb2/g' weaviate_grpc/*.py
sed -i ''  's/import base_pb2/from . import base_pb2/g' weaviate_grpc/*.py

echo "done"

