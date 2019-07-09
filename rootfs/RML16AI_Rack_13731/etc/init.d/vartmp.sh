#!/bin/sh
mount -n dev /dev -t tmpfs
cp -ar /prep/dev/* /dev
mount -n var /var -t tmpfs
cp -ar /prep/var/* /var
mount -n tmp /tmp -t tmpfs
echo 'vartmp done'