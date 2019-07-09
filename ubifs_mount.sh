#!/bin/bash
set -e

TARGET_DIR=/media/cdrom
SOURCE_IMG=rootfs.img

umount $TARGET_DIR 2>/dev/null || true
rmmod ubifs
rmmod ubi
rmmod mtdram
modprobe mtdram total_size=25600 erase_size=128
flash_erase /dev/mtd0 0 0
ubiformat /dev/mtd0  -f $SOURCE_IMG -v -O 64 -e 1
modprobe ubi mtd=0
mount -t ubifs /dev/ubi0_0 $TARGET_DIR
