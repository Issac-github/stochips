#!/bin/sh

# set -eux
set -eu

OUT_FILE=./src/main/protobuf/data_pb.js
OUT_TYPE_FILE=./src/main/protobuf/data_pb.d.ts
dir=`ls`
echo "gen dirs: $dir"

PROTO_FILES=$(find src -type f -name "*.proto")

if [ -z "$PROTO_FILES" ]; then
  echo "No .proto files found."
  exit 1
fi

echo "Proto files:"
echo $PROTO_FILES | sed 's/^/  - /'

# 先生成.d.ts
npx pbjs -t static-module -p . -w es6 -o $OUT_FILE $PROTO_FILES
npx pbts -o $OUT_TYPE_FILE $OUT_FILE
# 再生成js文件
npx pbjs -t json-module -p . -w es6 -o $OUT_FILE $PROTO_FILES
