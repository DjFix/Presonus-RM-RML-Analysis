#!/bin/bash
set -e

BINARY_NAME=$1
SYM_NAME=$2


SYM_DATA=$(readelf -Ws $BINARY_NAME | grep $SYM_NAME)
echo $SYM_DATA
SYM_OFFSET=$(echo $SYM_DATA | awk '{print $1}')
SYM_OFFSET=$(echo $SYM_OFFSET | tr -d ':')
#SYM_OFFSET=$((0x$SYM_OFFSET))
SYM_SIZE=$(echo $SYM_DATA | awk '{print $3}')
#SYM_OFFSET=$((0x$SYM_OFFSET))
echo sym offs \"$SYM_OFFSET\"
echo sym len \"$SYM_SIZE\"

CROSS_PREFIX=arm-linux-gnueabihf-

SECTION_BINARY=$BINARY_NAME.data

${CROSS_PREFIX}objcopy -j.data -O binary $BINARY_NAME $SECTION_BINARY
dd if=$SECTION_BINARY of=$SYM_NAME bs=1 skip=$SYM_OFFSET count=$SYM_SIZE