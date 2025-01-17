#!/usr/bin/env bash

set -euxo pipefail

for c in gcc-6 clang-6.0
do
    scons -Q \
          --enable-werror \
          --enable-tests \
          --enable-benchmarks \
          --enable-examples \
          --enable-doxygen \
          --build-3rdparty=openfec,google-benchmark \
          --compiler=$c \
          test
done
