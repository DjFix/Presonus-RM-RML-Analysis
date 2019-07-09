#!/bin/sh
# first, if we have a new app release, uncompress it
if [ -f /sfs/$1.tar.gz ]; then
    echo "Update firmware found, extracting..."
    tar xzf /sfs/$1.tar.gz -C /home/root
    rm /sfs/$1.tar.gz ]
fi
cd /home/root
# Compute MD5 sums of all the updated files. If they pass, 
# then launch the app.
md5sum -c $1.md5
if [ $? -eq 0 ]; then
    nohup ./$1 > /dev/null &
    exit 0
# If they fail, set the update failed flag and launch
# the backup app.
else
    echo "md5sum of app $1 failed!"
    touch /home/root/conf/update_failed
    nohup /home/root/release/$1 > /dev/null &
    exit 1
fi

