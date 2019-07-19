#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OUT_IMG="$(cd "$(dirname "$2")"; pwd)/$(basename "$2")"
UBI_IMG=$SCRIPT_DIR/rootfs.ubifs

echo $OUT_IMG
echo $UBI_IMG

mkfs.ubifs -vr $1 --min-io-size=128 -e 130944 -c 200 $UBI_IMG

cd $SCRIPT_DIR
ubinize -vo $OUT_IMG -Q 1606938876 -s 1 -m 128 -p 128KiB -O 64 $SCRIPT_DIR/ubifs.cfg

rm $UBI_IMG