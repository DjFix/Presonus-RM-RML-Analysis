#!/bin/sh

# The app needs this to know where to look for
# certain helper files such as device.txt
export HOME=/home/root
UPGRADESEL=`cat /proc/cmdline | grep upgrade`

if [ -f /sfs/devmode ]; then
    echo 'in development mode, not starting speaker!'
    if [ -f /sfs/nodefer ]; then
	echo 'not starting USB and network subsystems!'
    else
	/sbin/ifdown -a
	cat /proc/deferred_initcalls
	/etc/init.d/udev
	/sbin/ifup -a
    fi
else
    if [ -z $UPGRADESEL ]; then
	/sbin/ifdown -a
	/etc/init.d/udev
	echo 'starting speaker...'
	cd /home/root
	if [ -f /sfs/applog ]; then 
	    echo 'Logging app output.'
	    ./speaker > /home/root/speaker.log &
	else
	    ./speaker > /dev/null &
	fi
	echo 'speaker started'
	cat /proc/deferred_initcalls
	/sbin/ifup -a
    else
	/sbin/ifdown -a
	cat /proc/deferred_initcalls
	/etc/init.d/udev
	/sbin/ifup -a
	echo 'upgrading application...'
	/home/root/upgrade-app.sh
	echo 'starting speaker...'
	cd /home/root
	if [ -f /sfs/applog ]; then
	    echo 'Logging app output.'
	    ./speaker > /home/root/speaker.log &
	else
	    ./speaker > /dev/null &
	fi
	echo 'speaker started'
    fi
fi



