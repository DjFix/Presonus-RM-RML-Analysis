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

basedir=$(pwd)
ourname=$(basename "$0")
ourdir=`absolutePath "$basedir" "$(dirname "$0")"`
productName="FireWireKDP"
kextName="AppleFireWireKDP.kext"
kextPath="$ourdir/$kextName"
devKextPath="$ourdir/build/Debug-IOLog/$kextName"
depKextPath="$ourdir/build/Deployment/$kextName"
readMeFilename="FireWireKDP ReadMe.rtf"
sudoprompt="--- Enter account password for %u: "
year=`date | awk '{ print $6 }'`

i=`tput smso`	# inverse
ob=`tput rmso`	# off bold (off inverse?)
b=`tput bold`	# bold
u=`tput smul`	# underline
ou=`tput rmul`	# off underline

/bin/echo
/bin/echo "${u}${productName} Installer Script.${ou}"
/bin/echo "This script will install a kext and change this machine's boot-arg variables. This script should be run on the machine you wish to debug (target) as ${b}it will only install onto the current startup disk and modify the local machine${ob}."
/bin/echo
#if ! booleanAsk "--- Would you like to view the ${b}r${ob}eadme, ${b}c${ob}ontinue, or ${b}q${ob}uit? r|c|q > "
#then
#	exit 1
#fi
while :
do
	/bin/echo -n "--- Would you like to view the ${b}r${ob}eadme, ${b}c${ob}ontinue, or ${b}q${ob}uit? r|c|q > "; read reply
	
	case "$reply" in
		r | R | "readme" | "README" )
			open "${kextPath}/Contents/Resources/${readMeFilename}"
			if ! booleanAsk "--- Would you like to continue? y|n > "
			then
				exit 1
			fi
			break
			;;
		c | C | "continue" | "CONTINUE" )
			break
			;;
		q | Q | "quit" | "QUIT" )
			exit 1
			;;
	esac
			
	/bin/echo "What?"
done



#/bin/echo 
#/bin/echo "Looking for '$kextPath'..."

if ! [ -e "${kextPath}" ]
then
	if ! [ -e "${devKextPath}" ]
	then
		#if ! [ -e "${depKextPath}" ]	# could be dangerous while debugging
		#then
			/bin/echo "Could not find ${kextPath}"
			/bin/echo -n "--- Please type in the path to this kext: "; read reply
			if ! [ -e $reply ]
			then
				/bin/echo "Could not find AppleFireWireKPrintf.kext, exiting."
				exit 1
			fi
		#else
		#	kextPath="${depKextPath}"
		#	/bin/echo "Using ${i}deployment${ob} build kext @ '${kextPath}'"
		#fi
	else
		kextPath="${devKextPath}"
		/bin/echo "Using ${i}development${ob} build kext @ '${kextPath}'"
	fi
fi 

sudo -p "$sudoprompt" -v
sudo cp -R "${kextPath}" "/System/Library/Extensions"
sudo chown -R root:wheel "/System/Library/Extensions/${kextName}"
sudo touch /System/Library/Extensions/

# Deleteing these caches manually is highly discouraged.
# The recommended proceedure is to touch the Extensions
# folder, however, if the clock is wrong on your machine
# the touch can be ineffectual, so we still delete the
# caches manually in this case.  Bad us.
	
if [ $year -lt 2005 ]
then
	rm -f /System/Library/Extensions.mkext
	rm -f /System/Library/Extensions.kextcache
	rm -f /System/Library/Caches/com.apple.kernelcaches/*
fi

/bin/echo "${kextName} installed properlly."

bootargs=""

/bin/echo 
/bin/echo "${u}Boot-args options:${ou}"
/bin/echo
/bin/echo "	1)	debug=0x144 kdp_match_name=bogus"
/bin/echo "	2)	debug=0x146 kdp_match_name=bogus"
/bin/echo "	3)	debug=0x144 -v kdp_match_name=bogus"
/bin/echo "	4)	debug=0x146 -v kdp_match_name=bogus"
/bin/echo "	5)	Custom"
/bin/echo
/bin/echo -n "--- Select one of the boot-args above [4] > " ; read reply

if [ "$reply" == "" ]
then
	reply=4
fi
	
case "$reply" in

	1 )
		bootargs="debug=0x144 kdp_match_name=bogus"
		;;
	2 )
		bootargs="debug=0x146 kdp_match_name=bogus"
		;;
	3 )
		bootargs="debug=0x144 -v kdp_match_name=bogus"
		;;
	4 )
		bootargs="debug=0x146 -v kdp_match_name=bogus"
		;;
	* )
		/bin/echo "Without using quotes:"
		/bin/echo -n "--- sudo nvram boot-args=" ; read args
		bootargs="$args"
		;;
esac	

/bin/echo "Setting boot-args to '${bootargs}'"
if ! sudo nvram boot-args="${bootargs}"
then
	/bin/echo "Setting the NVRAM FAILED. You may try to modify the boot-args within the file located at '/Library/Preferences/SystemConfiguration/com.apple.Boot.plist'."
	/bin/echo -n "--- Would you like to open this file in 'pico'? [y]|n > " ; read reply
	if ! [ "$reply" == "n" ]
	then
		sudo pico /Library/Preferences/SystemConfiguration/com.apple.Boot.plist
	fi
else
	/bin/echo
	checkArgs=`sudo nvram boot-args`
	if [ "$checkArgs" != "boot-args	${bootargs}" ]
	then
		/bin/echo "Setting the NVRAM FAILED. You may try to modify the boot-args within the file located at '/Library/Preferences/SystemConfiguration/com.apple.Boot.plist'."
		/bin/echo -n"--- Would you like to open this file in 'pico'? [y]|n > " ; read reply
		if ! [ "$reply" == "n" ]
		then
			sudo pico /Library/Preferences/SystemConfiguration/com.apple.Boot.plist
		fi
	else
		/bin/echo "${u}${productName} installation successful.${ou}"
	fi
fi

if booleanAsk "--- Would you like to restart? y|n > "
then
	sync
	/bin/echo -n "--- Save your work! Continue? [y]|n > " ; read reply
	if ! [ "$reply" == "n" ]
	then
		/bin/echo "Rebooting..."
		sudo reboot
	fi
fi


