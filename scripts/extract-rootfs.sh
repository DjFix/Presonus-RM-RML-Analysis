#!/bin/bash

trap ctrl_c INT

function ctrl_c() {
    echo -e "\n ** Trapped CTRL-C"
    umount $TMP
    rm -rf $TMP
    exit 0
}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

WORKDIR=$DIR/..

FIRMWARES=$(find $WORKDIR/firmware/ -type d)

for item in $FIRMWARES
do
    BASENAME=${item##*/}
    if [[ ! -z $BASENAME ]]; then
	echo "Extracting: $BASENAME from $item"
    fi
    EX_DIR=$WORKDIR/rootfs/$BASENAME
    mkdir -p $EX_DIR

    TMP="$(mktemp -d)"
    $DIR/ubifs_mount.sh $WORKDIR/firmware/$BASENAME/rootfs.img $TMP
    
    cp -a $TMP/* $EX_DIR
    
    umount $TMP
    rm -rf $TMP
done