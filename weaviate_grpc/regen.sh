#!/bin/bash

echo "this script assumes that you have checked out weaviate next to the client"
cd "${0%/*}/.."


python3 -m grpc_tools.protoc  -I ../weaviate/grpc --python_out=./weaviate_grpc --pyi_out=./weaviate_grpc --grpc_python_out=./weaviate_grpc ../weaviate/grpc/weaviate.proto


sed -i ''  's/import weaviate_pb2/from . import weaviate_pb2/g' weaviate_grpc/weaviate_pb2_grpc.py

echo "done"