Continuous integration
**********************

.. contents:: Table of contents:
   :local:
   :depth: 2

Overview
========

GitHub Actions are configured to build ``master`` and ``develop`` branches and pull requests.

GitHub Actions build Roc for Linux and macOS. Linux worker uses Docker to run builds on several Linux distros. Linux worker also uses QEMU to run cross-compiled tests.

Docker images for continuous integration and cross-compilation are prepared using Docker Hub automated builds. They are based on official upstream images, adding pre-installed packages required for build. Dockerfiles for images are hosted in a separate GitHub repository. When a Dockerfile or an upstream image changes, Docker Hub automatically triggers rebuild.

If images build have to be customized with build arguments it can be accomplished by using :ref:`build hooks <build_hooks>`.

Links:
 * `GitHub Actions page <https://github.com/roc-streaming/roc-toolkit/actions>`_
 * `GitHub Actions configuration <https://github.com/roc-streaming/roc-toolkit/blob/master/.github/workflows/build.yml>`_
 * `Docker Hub organization <https://hub.docker.com/u/rocstreaming/>`_
 * `Dockerfiles repo <https://github.com/roc-streaming/dockerfiles>`_

Docker images
=============

The following Docker images are used on our CI builds.

Linux native
------------

=================================== ===================== ============= ==================================
Image                               Base image            Architecture  Compilers
=================================== ===================== ============= ==================================
rocstreaming/env-ubuntu:22.04       ubuntu:22.04          x86_64        gcc-11, gcc-12, clang-11, clang-14
rocstreaming/env-ubuntu:20.04       ubuntu:20.04          x86_64        gcc-8, gcc-10, clang-8, clang-10
rocstreaming/env-ubuntu:18.04       ubuntu:18.04          x86_64        gcc-6, clang-6
rocstreaming/env-ubuntu:16.04       ubuntu:16.04          x86_64        gcc-4.8, clang-3.7
rocstreaming/env-ubuntu:14.04       ubuntu:14.04          x86_64        gcc-4.4, clang-3.4
rocstreaming/env-ubuntu-minimal     ubuntu:latest         x86_64        distro default
rocstreaming/env-debian             debian:stable         x86_64        distro default
rocstreaming/env-fedora             fedora:latest         x86_64        distro default
rocstreaming/env-centos             centos:latest         x86_64        distro default
rocstreaming/env-opensuse           opensuse/leap:latest  x86_64        distro default
rocstreaming/env-archlinux          archlinux/base:latest x86_64        distro default
rocstreaming/env-alpine             alpine:latest         x86_64        distro default
=================================== ===================== ============= ==================================

Linux toolchains
----------------

============================================================== ============= =========
Image                                                          Architecture  Compilers
============================================================== ============= =========
rocstreaming/toolchain-aarch64-linux-gnu:gcc-7.4               armv8         gcc-7.4
rocstreaming/toolchain-arm-linux-gnueabihf:gcc-4.9             armv7         gcc-4.9
rocstreaming/toolchain-arm-bcm2708hardfp-linux-gnueabi:gcc-4.7 armv6         gcc-4.7
============================================================== ============= =========

Android toolchains
------------------

========================================== =========== =================================== =============
Image                                      APIs        ABIs                                Compilers
========================================== =========== =================================== =============
rocstreaming/toolchain-linux-android:ndk21 21-29       armeabi-v7a, arm64-v8a, x86, x86_64 clang-9.0.8
========================================== =========== =================================== =============

Full Android environment
------------------------

========================================== ===============================
Image                                      JDK
========================================== ===============================
rocstreaming/env-android:jdk11             openjdk:11.0.7-jdk-slim-buster
rocstreaming/env-android:jdk8              openjdk:8u252-jdk-slim-buster
========================================== ===============================

Running CI builds locally
=========================

It is possible to run Docker-based builds locally, in the same environment as they are run on CI.

For example, this will run Fedora build:

.. code::

   $ scripts/ci_checks/docker.sh rocstreaming/env-fedora \
       scripts/ci_checks/linux-x86_64/fedora.sh

You can also invoke Docker manually:

.. code::

    $ docker run -t --rm --cap-add SYS_PTRACE -u "${UID}" -v "${PWD}:${PWD}" -w "${PWD}" \
        rocstreaming/env-fedora \
          scons --build-3rdparty=openfec,cpputest --enable-debug test

Explanation:

* ``-t`` allocates a pseudo-TTY to enable color output
* ``--rm`` removes the container when the command exits
* ``--cap-add SYS_PTRACE`` enables ptracing which is needed for clang sanitizers
* ``-u "${UID}"`` changes the UID inside the container from root to the current user
* ``-v "${PWD}:${PWD}"`` mounts the current directory into the container at the same path
* ``-w "${PWD}"`` chdirs into that directory

Working with Docker images
==========================

`Docker images <https://github.com/roc-streaming/dockerfiles>`_ are built using `GitHub actions <https://github.com/roc-streaming/dockerfiles/blob/main/.github/workflows/build.yml>`_ and then pushed to Docker Hub.

Each image directory contains one or several dockerfiles and ``images.csv`` file in the following format:

.. code::

    DOCKERFILE;ARGS (comma-separated list);TAG

This file defines what tags to build, path to dockerfile and build arguments for each tag. Build arguments are passed as ARGs to ``docker build``.

If the value in the first column is left empty, it defaults to ``Dockerfile`` is in the same directory as ``images.csv``. If the value in the last column is omitted, it defaults to the name of the directory which contains Dockerfile, e.g. if Dockerfile path is ``14.04/Dockerfile``, then tag defaults to ``14.04``.

Example:

.. code::

    DOCKERFILE;ARGS (comma-separated list);TAG
    Dockerfile;MAJOR=4.9,MINOR=4,DATE=2017.01;gcc-4.9
    Dockerfile;MAJOR=7.4,MINOR=1,DATE=2019.02;gcc-7.4
    Dockerfile;MAJOR=7.4,MINOR=1,DATE=2019.02;latest

This file defines three tags: ``gcc-4.9``, ``gcc-7.4``, and ``latest``. Each tag uses the same ``Dockerfile`` and different arguments ``MAJOR``, ``MINOR``, and ``DATE``.

You can build all docker images locally using:

.. code::

   ./scripts/run_all.sh --build

Or build specific image:

.. code::

    cd images/<image_name>
    ../../scripts/build.sh

Android environment
===================

The ``env-android`` images provide a full android environment.
In particular the following packages are availables:

* android platforms
* android build tools
* android ndk
* android cmake
* android emulator
* adb and platform tools

For reducing image size and have more granularity over various tools versions, those packages are installed only when container runs, i.e. at container entrypoint.

The following environment variables can be passed at container run for choosing a specified version:

* API
* BUILD_TOOLS_VERSION
* NDK_VERSION
* CMAKE_VERSION

Example:

.. code::

    $ docker run -t --rm -v "${PWD}:${PWD}" -w "${PWD}" -v android-sdk:/sdk --env API=28 \
      --env NDK_VERSION=21.1.6352462 --env BUILD_TOOLS_VERSION=29.0.3 \
        rocstreaming/env-android:jdk8 \
          scons -Q --compiler=clang --host=aarch64-linux-android28 \
            --disable-soversion \
            --disable-tools \
            --disable-examples \
            --disable-tests \
            --disable-pulseaudio \
            --disable-sox \
            --build-3rdparty=libuv,openfec

Tools caching
-------------

If a named volume is mounted at `/sdk` path in the container (for example by using `-v android-sdk:/sdk` option), next run of the image will not install again components already installed previously.

If it's needed to mount the volume to a specific host location (the host location must exist) it can be achieved by adding the following options to the docker command:

.. code::

    --mount type=volume,dst=/sdk,volume-driver=local,volume-opt=type=none,volume-opt=o=bind,volume-opt=device=<host-path>

Emulator
--------

The android emulator can use hardware acceleration features to improve performance, sometimes drastically.

.. note::
  According to `official emulator acceleration docs <https://developer.android.com/studio/run/emulator-acceleration>`_:

  To use VM acceleration, your development environment must meet the following requirements:

    SDK Tools: minimum version 17; recommended version 26.1.1 or later
    AVD with an x86-based system image, available for Android 2.3.3 (API level 10) and higher

      Warning: AVDs that use ARM- or MIPS-based system images can't use the VM acceleration.

  In addition to the development environment requirements, your computer's processor must support one of the following virtualization extensions technologies:

    Intel Virtualization Technology (VT, VT-x, vmx) extensions
    AMD Virtualization (AMD-V, SVM) extensions

Linux-based systems support VM acceleration through the `KVM software package <https://www.linux-kvm.org/page/Main_Page>`_.

For enabling hardware acceleration run the container in privileged mode, i.e. by using ``--privileged`` flag.

.. warning::

  Since CI runs jobs already on a virtual environment, if the emulator need to be run on CI, the ``env-android`` image must be run with ``--privileged`` option for allowing virtualization nesting.

To see if acceleration is available use:

.. code::

    $ emulator -accel-check
    accel:
    0
    KVM (version 12) is installed and usable.

To create an Android Virtual Device (AVD) and run the emulator:

* download the emulator system image:

  .. code::

      $ yes | sdkmanager <system-image>

  where ``<system-image>`` is in the list offered by ``sdkmanager --list``

* create the AVD:

  .. code::

      $ echo no | avdmanager create avd --name <avd-name> --package <system-image>

* launch emulator (use ``-accel on`` or ``-accel off`` depending of hardware acceleration availability):

  .. code::

      $ emulator -avd <avd-name> -no-audio -no-boot-anim -no-window -gpu off -accel [on/off] &

* check the AVD status:

  .. code::

      $ adb devices
      List of devices attached
      emulator-xxxx device
      # "device" indicates that boot is completed
      # "offline" indicates that boot is still going on

Device script
-------------

The ``env-android`` image provides an helper script named ``device`` that takes care of creating and booting up AVDs.

* create an AVD:

  .. code::

      $ device create --api=<API> --image=<IMAGE> --arch=<ARCH> --name=<AVD-NAME>

  The string ``"system-images;android-<API>;<IMAGE>;<ARCH>"`` defines the emulator system image to be installed (it must be present in the list offered by ``sdkmanager --list``)

* start device and wait until boot is completed

  .. code::

      $ device start --name=<AVD-NAME>

.. _build_hooks:
