#!/bin/sh

# See if we're in development mode
if [ -f /sfs/devmode ]; then
    # Copy the application to /home/root
    cd /sfs/
    cp $1_dsp.out /home/root
    cp $1 /home/root

    # Is this a speaker app?
    if [ $1 == "speaker" ]; then
        mkdir /home/root/presets
        cp -r presets/* /home/root/presets
    else
	echo ''
    fi

    # Execute the copied app
    cd /home/root
    ./$1
else
    # We're not in development mode.  Bail!
    echo 'Cannot execute! In production mode.'
fi
