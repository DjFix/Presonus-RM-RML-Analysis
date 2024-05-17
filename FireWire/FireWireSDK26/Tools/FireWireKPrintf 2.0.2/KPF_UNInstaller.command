#!/bin/sh -


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

	/bin/echo "$abspath_outputpath"
	
	return 0
}

booleanAsk ()
{
	local reply

	if [ "$noprompt" == "" ]
	then

		while :
		do
			/bin/echo -n "$1"
			read reply
	
			case "$reply" in
				y | Y | yes | YES )
					return 0
					;;
				n | N | no | NO )
					return 1
					;;
			esac
			
			/bin/echo "What?"
			
		done

	else
		return 0
	fi
}

# main
#######

kextName="AppleFireWireKPrintf.kext"
kextPath="/System/Library/Extensions/${kextName}"
sudoprompt="--- Enter account password for %u: "
year=`date | awk '{ print $6 }'`

/bin/echo
/bin/echo "FireWireKPrintf UN-Installer Script."

sudo -p "$sudoprompt" -v

if [ -e "${kextPath}" ]
then
	sudo rm -Rf "${kextPath}"
fi
sudo touch /System/Library/Extensions/

# Deleteing these caches manually is highly discouraged.
# The recommended procedure is to touch the Extensions
# folder, however, if the clock is wrong on your machine
# the touch can be ineffectual, so we still delete the
# caches manually in this case.  Bad us.
	
if [ $year -lt 2006 ]
then
	sudo rm -f /System/Library/Extensions.mkext
	sudo rm -f /System/Library/Extensions.kextcache
	sudo rm -f /System/Library/Caches/com.apple.kernelcaches/*
fi

sudo nvram -d boot-args

# rewrite boot.plist
bootPlist="/Library/Preferences/SystemConfiguration/com.apple.Boot.plist"

sudo /bin/echo '<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Kernel</key>
	<string>mach_kernel</string>
	<key>Kernel Flags</key>
	<string></string>
</dict>
</plist>' > "/tmp/newboot.plist"
sudo mv /tmp/newboot.plist "${bootPlist}"

/bin/echo "Please disconnect all FireWire cables from this Mac. Also, restart the 2nd Mac which was running fwkpfv or FireWireKPrintfViewer."

if booleanAsk "--- This machine needs to be restarted. Would you like to restart now? y|n > "
then
	sudo shutdown -r now
fi
