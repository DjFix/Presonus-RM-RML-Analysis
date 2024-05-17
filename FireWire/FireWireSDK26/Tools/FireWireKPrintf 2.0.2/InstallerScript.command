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
kextName="AppleFireWireKPrintf.kext"
kextPath="$ourdir/$kextName"
devKextPath="$ourdir/build/Development/$kextName"
depKextPath="$ourdir/build/Deployment/$kextName"
readMeFilename="FireWireKPrintf ReadMe.rtf"
sudoprompt="--- Enter account password for %u: "
year=`date | awk '{ print $6 }'`

i=`tput smso`	# inverse
ob=`tput rmso`	# off bold (off inverse?)
b=`tput bold`	# bold
u=`tput smul`	# underline
ou=`tput rmul`	# off underline

/bin/echo
/bin/echo "${u}FireWireKPrintf Installer Script.${ou}"
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
		#	/bin/echo "Using ${b}deployment${ob} build kext @ '${kextPath}'"
		#fi
	else
		kextPath="${devKextPath}"
		/bin/echo "Using ${b}development${ob} build kext @ '${kextPath}'"
	fi
fi 

sudo -p "$sudoprompt" -v
sudo cp -R "${kextPath}" "/System/Library/Extensions"
sudo chown -R root:wheel "/System/Library/Extensions/${kextName}"
sudo touch /System/Library/Extensions/

# Deleteing these caches manually is highly discouraged.
# The recommended procedure is to touch the Extensions
# folder, however, if the clock is wrong on your machine
# the touch can be ineffectual, so we still delete the
# caches manually in this case.  Bad us.
	
if [ $year -lt 2006 ]
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
/bin/echo "	1)	debug=0x8"
/bin/echo "	2)	debug=0x14e"
/bin/echo "	3)	debug=0x14e -v"
/bin/echo "	4)	debug=0x14e io=0x80"
/bin/echo "	5)	debug=0x14e io=0x80 -v"
/bin/echo "	6)	debug=0xd4e io=0x80 -v"
/bin/echo "	7)	Custom"
/bin/echo
/bin/echo -n "--- Select one of the boot-args above [2] > " ; read reply

if [ "$reply" == "" ]
then
	reply=2
fi
	
case "$reply" in

	1 )
		bootargs="debug=0x8"
		;;
	2 )
		bootargs="debug=0x14e"
		;;
	3 )
		bootargs="debug=0x14e -v"
		;;
	4 )
		bootargs="debug=0x14e io=0x80"
		;;
	5 )
		bootargs="debug=0x14e io=0x80 -v"
		;;
	6 )
		bootargs="debug=0xd4e io=0x80 -v"
		;;
	* )
		/bin/echo "Without using quotes:"
		/bin/echo -n "--- nvram boot-args=" ; read args
		bootargs="$args"
		;;
esac	

timefrmt=0
/bin/echo 
/bin/echo "${u}FireWireKPrintf time format:${ou}"
/bin/echo
/bin/echo "	0)	Converted FW Cycle Time Units"
/bin/echo "	1)	Absolute Time Units"
/bin/echo "	2)	FireWire Time Units"
/bin/echo "	3)	Nanoseconds Time Units"
/bin/echo "	4)	Microseconds Time Units"
/bin/echo "	5)	Milliseconds Time Units"
/bin/echo "	6)	Seconds Time Units"
/bin/echo "	7)	Day Time Units"
/bin/echo "	8)	No Time Units"
/bin/echo
/bin/echo -n "--- Select one of the time formats above [4] > " ; read reply

if [ "$reply" == "" ]
then
	reply=4
fi
	
case "$reply" in

	0 )
		timefrmt=0
		;;
	1 )
		timefrmt=1
		;;
	2 )
		timefrmt=2
		;;
	3 )
		timefrmt=3
		;;
	4 )
		timefrmt=4
		;;
	5 )
		timefrmt=5
		;;
	6 )
		timefrmt=6
		;;
	7 )
		timefrmt=7
		;;
	8 )
		timefrmt=8
		;;
	* )
		/bin/echo "Did understand your response. Setting format to 'Converted FW Cycle Time Units'"
		timefrmt=0
		;;
esac	

options=0
/bin/echo 
/bin/echo "${u}FireWireKPrintf options:${ou}"
/bin/echo
/bin/echo -n "--- Enable Time Units Padding? y|[n] > " ; read reply
if [ "$reply" == "y" ]
then
	options=`expr $options + 16`
fi

/bin/echo -n "--- Disable FireWireKPrintf's verbose printing? y|[n] > " ; read reply
if [ "$reply" == "y" ]
then
	options=`expr $options + 256`
fi

#/bin/echo -n "--- ${b}Disable${ob} Synchronous Mode? y|[n] > " ; read reply
#if [ "$reply" == "y" ]
#then
#	options=`expr $options + 1024`
#fi

fwkpf=`expr $timefrmt + $options`

/bin/echo "Setting boot-args to '${bootargs} fwkpf=$fwkpf'"
#sudo nvram boot-args="$bootargs fwkpf=$fwkpf"
if ! sudo nvram boot-args="${bootargs} fwkpf=${fwkpf}"
then
	/bin/echo "Setting the NVRAM FAILED. You may try modifing the boot-args (Kernel Flags) within the file located at '/Library/Preferences/SystemConfiguration/com.apple.Boot.plist'."
	/bin/echo -n "--- Would you like to open this file in 'pico'? [y]|n > " ; read reply
	if ! [ "$reply" == "n" ]
	then
		sudo pico /Library/Preferences/SystemConfiguration/com.apple.Boot.plist
	fi
fi

/bin/echo
/bin/echo "${u}Installation successful.${ou}"
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


