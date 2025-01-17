#!/usr/bin/env bash

set -euxo pipefail

for pulse in 12.2 14.2 15.99.1
do
    scons -Q \
          --enable-werror \
          --enable-tests \
          --enable-examples \
          --build-3rdparty=openfec,pulseaudio:$pulse \
          test
done
