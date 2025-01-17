#!/usr/bin/env bash

set -euxo pipefail

for c in gcc-4.8 clang-3.7
do
    scons -Q \
          --enable-werror \
          --enable-tests \
          --enable-benchmarks \
          --enable-examples \
          --enable-doxygen \
          --build-3rdparty=libatomic_ops,openfec,google-benchmark \
          --compiler=$c \
          test
done
