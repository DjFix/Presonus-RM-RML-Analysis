#!/bin/bash

set -e

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

if [ -z ${BUILDROOT_DIR+x} ]; then
    echo "Please set BUILDROOT_DIR env variable"
    exit
fi

cp ${BUILDROOT_DIR}/output/build/linux-5.2.11/.config $SCRIPTPATH/linux
cp ${BUILDROOT_DIR}/.config $SCRIPTPATH/buildroot
cp ${BUILDROOT_DIR}/output/build/uboot-2018.11/.config $SCRIPTPATH/u-boot
cp ${BUILDROOT_DIR}/output/build/linux-5.2.11/arch/arm/boot/dts/da850-presonus.dts $SCRIPTPATH
cp ${BUILDROOT_DIR}/output/build/linux-5.2.11/arch/arm/boot/dts/da850.dtsi $SCRIPTPATH

