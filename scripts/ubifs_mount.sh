#!/bin/bash
set -e

if ! [ -x "$(command -v flash_erase)" ]; then
  echo Command 'flash_erase' not found, but can be installed with:
  echo sudo apt install mtd-utils
  exit 1
fi

TARGET_DIR=${2:-/media/cdrom}
SOURCE_IMG=$1

umount $TARGET_DIR 2>/dev/null || true
rmmod ubifs || true
rmmod ubi || true
rmmod mtdram || true
modprobe mtdram total_size=25600 erase_size=128
flash_erase /dev/mtd0 0 0
ubiformat /dev/mtd0 -f $SOURCE_IMG -O 64 -e 1 -s 1
modprobe ubi mtd=0
mount -t ubifs /dev/ubi0_0 $TARGET_DIR