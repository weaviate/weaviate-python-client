#!/bin/bash

branchOrTag="${1:-main}"
dir="tools"
out="weaviate/proto"
mkdir -p ${dir}
curl -LkSs https://api.github.com/repos/weaviate/weaviate/tarball/${branchOrTag} -o ${dir}/weaviate.tar.gz
tar --strip-components=3 -C ${dir} -xvf ${dir}/weaviate.tar.gz $(tar -tf ${dir}/weaviate.tar.gz | grep '^weaviate-weaviate-[^/]\+/grpc/proto/v1')

python3 -m grpc_tools.protoc  -I ${dir} --python_out="./${out}" --pyi_out="./${out}" --grpc_python_out="./${out}" ${dir}/v1/*.proto

rm ${dir}/weaviate.tar.gz

sed -i ''  's/from v1/from weaviate.proto.v1/g' ${out}/v1/*.py
sed -i ''  's/from v1/from weaviate.proto.v1/g' ${out}/v1/*.pyi

rm -rf ${dir}/v1

echo "done"