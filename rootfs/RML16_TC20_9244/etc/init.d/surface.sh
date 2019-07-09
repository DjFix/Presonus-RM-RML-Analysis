#!/bin/sh

# The app needs this to know where to look for
# certain helper files such as device.txt
export HOME=/home/root

if [ -f /sfs/devmode ]; then
    echo 'in development mode, not starting surface!'
    if [ -f /sfs/nodefer ]; then
	echo 'not starting USB and network subsystems!'
    else
	/sbin/ifdown -a
	cat /proc/deferred_initcalls
	/etc/init.d/udev
	/sbin/ifup -a
    fi
else
    if [ -f /sfs/nodefer ]; then
	echo 'not deferring init of USB and network subsystems'
	/sbin/ifdown -a
	cat /proc/deferred_initcalls
	/etc/init.d/udev
	/sbin/ifup -a
	echo 'starting surface...'
	cd /home/root
	./surface > /dev/null &
	echo 'surface started'
    else
	/sbin/ifdown -a
    /usr/bin/psplash-write "PROGRESS 10"
	/etc/init.d/udev
    /usr/bin/psplash-write "PROGRESS 15"
	echo 'starting surface...'
	cd /home/root
	if [ -f /sfs/applog ]; then
	    echo 'Logging app output.'
	    ./surface > /home/root/surface.log &
	else
	    ./surface > /dev/null &
	fi
	echo 'surface started'
	cat /proc/deferred_initcalls
    /usr/bin/psplash-write "PROGRESS 20"
	/sbin/ifup -a
    /usr/bin/psplash-write "PROGRESS 25"
    fi
fi




