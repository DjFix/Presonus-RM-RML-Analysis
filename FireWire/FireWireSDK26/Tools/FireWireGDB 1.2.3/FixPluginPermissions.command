#!/bin/sh

# SetPluginPermissions.sh
# FireWireGDB
#
# Created by Carlos on 4/4/06.
# Copyright 2006 Apple Computer, Inc. All rights reserved.
#
# gdb-469+ requires that plugins belong to a group with the same (or higher) privledges as gdb.
# gdb-437 is setgid "procmod", so this script sets each plugin to "procmod +s"

absolutePath()
{
	local abspath_basedir abspath_inputpath abspath_outputpath abspath_tmppath
	
	abspath_basedir="$1"
	abspath_inputpath="$2"
	
	abspath_tmppath="$abspath_inputpath"
	while :
	do
		abspath_tmppath=$(dirname "$abspath_tmppath")
		if [ "$abspath_tmppath" == "." ]
		then
			abspath_outputpath="$abspath_basedir"/"$abspath_inputpath"
			break
		fi
		
		if [ "$abspath_tmppath" == "/" ]
		then
			abspath_outputpath="$abspath_inputpath"
			break
		fi
		
	done

	echo "$abspath_outputpath"
	
	return 0
}

basedir=$(pwd)
ourname=$(basename "$0")
ourdir=`absolutePath "$basedir" "$(dirname "$0")"`
sudoprompt="--- Enter account password for %u: "

pluginFileNames=("FireWirePluginPPC-Panther" "FireWirePluginPPC-Tiger" "FireWirePlugini386-Chardonnay" "FireWirePlugini386-Chardonnay-later" "FireWirePlugini386-Leopard" "FireWirePluginPPC32-Leopard")

echo 
echo "FireWireGDB SetPluginPermission script - This script will adjust the permissions on all plugins that reside within the same directory as it. These permission changes to the plugins are required for use with later versions of GDB."
echo
sudo -p "$sudoprompt" -v

cd "$ourdir"
#echo $ourdir

count=${#pluginFileNames[@]}
index=0
while [ "$index" -lt "$count" ]
do
	plugin=${pluginFileNames[$index]}
	
	if ! [ -e "$plugin" ]
	then
		echo "Did not find $plugin"
	else
		sudo chgrp procmod "$plugin"
		sudo chmod g+s "$plugin"
		echo "Updated $plugin"
	fi
	
	let "index = $index + 1"
done