#!/bin/sh

# The app needs this to know where to look for
# certain helper files such as device.txt
export HOME=/home/root

if [ -f /sfs/devmode ]; then
    echo 'in development mode, not starting mixer!'
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
	echo 'starting mixer...'
	cd /home/root
	./mixer > /dev/null &
	echo 'mixer started'
    else
	/sbin/ifdown -a
	/etc/init.d/udev
	echo 'starting mixer...'
	cd /home/root
	if [ -f /sfs/applog ]; then
	    echo 'Logging app output.'
	    ./mixer > /home/root/mixer.log &
	else
	    ./mixer > /dev/null &
	fi
	echo 'mixer started'
	cat /proc/deferred_initcalls
	/sbin/ifup -a
    fi
fi

#/etc/init.d/dropbear start


