#!/usr/bin/env bash

set -euxo pipefail

for c in gcc-8 gcc-10 clang-8 clang-10
do
    scons -Q \
          --enable-werror \
          --enable-tests \
          --enable-benchmarks \
          --enable-examples \
          --build-3rdparty=openfec \
          --compiler=$c \
          test
done
