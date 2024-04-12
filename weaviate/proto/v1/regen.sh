#!/bin/bash

echo "this script assumes that you have checked out weaviate next to the client"
cd "${0%/*}/.."


python3 -m grpc_tools.protoc  -I ../../../weaviate/grpc/proto --python_out=./ --pyi_out=./ --grpc_python_out=./ --grpclib_python_out=. ../../../weaviate/grpc/proto/v1/*.proto

sed -i ''  's/from v1/from weaviate.proto.v1/g' v1/*.py
sed -i ''  's/from v1/from weaviate.proto.v1/g' v1/*.pyi
sed -i ''  's/v1/weaviate.proto.v1/g' v1/weaviate_grpc.py
sed -i ''  's/\/weaviate.weaviate.proto.v1/\/weaviate.v1/g' v1/weaviate_grpc.py

echo "done"
