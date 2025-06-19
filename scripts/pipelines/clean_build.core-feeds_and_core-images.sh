#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname "${BASH_SOURCE[0]}"))

SCRIPT_ROOT1=${SCRIPT_ROOT}

. "${SCRIPT_ROOT}/build.common.sh" $@

echo "INFO: Cleaning and building the core package feed."

bitbake -c cleanall packagefeed-ni-core
bitbake -c cleanall package-index
bitbake -c cleanall linux-nilrt

. "${SCRIPT_ROOT1}/build.core-feeds.sh" $@

bitbake -c cleanall nilrt-safemode-rootfs
bitbake -c cleanall nilrt-base-system-image
bitbake -c cleanall nilrt-recovery-media

. "${SCRIPT_ROOT1}/build.core-images.sh" $@
