#!/bin/bash
set -eu
TOOLCHAIN='docker.io/library/gcc@sha256:b99b86a28812b1e6453a231a947dc43d76fe192788a12f344a9b568bf9f5d24c'
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUTPUT=${1:-"$PWD/vc_validate"}
OUTPUT_DIR=$(dirname -- "$OUTPUT")
OUTPUT_NAME=$(basename -- "$OUTPUT")
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(CDPATH= cd -- "$OUTPUT_DIR" && pwd)
docker run --rm --platform linux/amd64 \
  -v "$SOURCE_DIR:/src:ro" \
  -v "$OUTPUT_DIR:/out" \
  "$TOOLCHAIN" \
  g++ -std=c++11 -O3 -o "/out/$OUTPUT_NAME" /src/vc_validate.cpp
