# Digging Presonus RML16AI

Presonus has deprecated ther RM/RML series mixer. That mostly means that support for this great piece of hardware is dropped too. 
Last firmware update has been released on Sep, 13th 2018 under the version of v13731. It brings some improvements and features, but still has some issues.

I've reported that issues to presonus in Dec 2018-Jan 2019, but no fixes was released up to date. Well, I've decided to take a look into it by myself.

## Update Bundle structure

`RML16AI_Rack_13731` Update bundle consists of the following files:

* `initvars.scr`
* `recovery.scr`
* `rootfs.img`
* `uImage`
* `upgrade.bin`

`.scr` files are basically custom uBoot scripts, that run specific update commands. That files has a simple signature header, that is used for 
early Bundle fingerptinting. I think the basic usage of it verificaton that certain update Bundle will fit the hardware it is running on. We'll 
analyze this headers later and see if we can run cross-upgrade in the family. Cross-upgrade will allow us to turn RM/RML16 into 
full-featured RM/RML32 machine, because the hardware in this machines seems to be identical. I state it after in-depth analysis of hardware of
my own RML16AI.

### `uImage`

This is the linux kernel used to boot the mixer during upgrade process. This is also seems to be the kernel that is flashed as upgrade

### `rootfs.img`

This is the rootfs UBIFS image. We'll examine it's contents later

### `upgrade.bin`

tar.gz with unstripped ELF mixer binary and MD5 sum file. Can be extracted with

```
$ tar xzf upgrade.bin
```

### Contents of `initvars.scr`

This is U-Boot script image. This script seems to be started first and pass control to `recovery.scr` or flash update by itself.

this file is compiled with `mkimage` tool. See example [here](https://www.denx.de/wiki/view/DULG/UBootScripts)

install u-boot-tools
```
$ apt install u-boot-tools
```

```
$ dumpimage -l initvars.scr
Image Name:   Default Environment
Created:      Tue Jul 26 20:08:26 2016
Image Type:   ARM Linux Script (uncompressed)
Data Size:    672 Bytes = 0.66 kB = 0.00 MB
Load Address: 00000000
Entry Point:  00000000
Contents:
   Image 0: 664 Bytes = 0.65 kB = 0.00 MB
```

this images is generated with
```
$ mkimage -T script -C none -n 'Default Environment' -A arm -d testscript.raw testscript.scr
Image Name:   Default Environment
Created:      Wed Jul 10 11:25:35 2019
Image Type:   ARM Linux Script (uncompressed)
Data Size:    672 Bytes = 0.66 kB = 0.00 MB
Load Address: 00000000
Entry Point:  00000000
Contents:
   Image 0: 664 Bytes = 0.65 kB = 0.00 MB
```

where `testscript.raw` is raw script
```
setenv bootargs_norfs 'mem=32M console=ttyS2,115200n8 root=/dev/mtdblock2 rootfs type=jffs2 ip=off quiet'
setenv bootcmd_norfs 'setenv bootargs ${bootargs_norfs};bootm 0x600A0000'
setenv bootcmd_fullrecovery 'usb start;if fatload usb 0:1 0xC0000000 recovery.scr;then source 0xC0000000;else run bootcmd_norfs;fi'
setenv bootcmd 'run bootcmd_fullrecovery'
setenv cpkernel 'erase 0x600A0000 0x604FFFFF;usb start;fatload usb 0:1 0xC0000000 uImage;cp.b 0xC0000000 0x600A0000 $filesize'
setenv cprootfs 'erase 0x60500000 0x615FFFFF;usb start;fatload usb 0:1 0xC0000000 cramfs.img;cp.b 0xC0000000 0x60500000 $filesize'
setenv cpsystem 'run cpkernel;run cprootfs;usb stop'
```

### Contents of `recovery.scr`

This is U-Boot script image. This is the main update script, that flashes new update into internal NAND flash

```
apt install u-boot-tools
```

Raw script
```
echo "Beginning Recovery Process..."

# Alert LCD screen of a recovery
mw.b 0x01C42000 0x41   #A
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x67   #g
mw.b 0x01D0C000 0x41   #A
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x67   #g

# Erase the area where the kernel image will live
erase 0x600A0000 0x604FFFFF
usb start

# Show 10% done
mw.b 0x01C42000 0x41   #A
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x39   #9
mw.b 0x01C42000 0x67   #g
mw.b 0x01D0C000 0x41   #A
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x39   #9
mw.b 0x01D0C000 0x67   #g

# Read the kernel image off the USB stick
# Load it into ram.  Copy byte by byte into flash
fatload usb 0:1 0xC0000000 uImage
cp.b 0xC0000000 0x600A0000 $filesize

# Show 25% done
mw.b 0x01C42000 0x41   #A
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x31   #1
mw.b 0x01C42000 0x39   #9
mw.b 0x01C42000 0x67   #g
mw.b 0x01D0C000 0x41   #A
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x31   #1
mw.b 0x01D0C000 0x39   #9
mw.b 0x01D0C000 0x67   #g

# Erase where the file system lives.
# Load it into RAM
erase 0x60500000 0x61BFFFFF

# Show 40% done
mw.b 0x01C42000 0x41   #A
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x32   #2
mw.b 0x01C42000 0x38   #8
mw.b 0x01C42000 0x67   #g
mw.b 0x01D0C000 0x41   #A
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x32   #2
mw.b 0x01D0C000 0x38   #8
mw.b 0x01D0C000 0x67   #g

fatload usb 0:1 0xC0000000 rootfs.img

# Show 50% done
mw.b 0x01C42000 0x41   #A
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x33   #3
mw.b 0x01C42000 0x32   #2
mw.b 0x01C42000 0x67   #g
mw.b 0x01D0C000 0x41   #A
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x33   #3
mw.b 0x01D0C000 0x32   #2
mw.b 0x01D0C000 0x67   #g

# Copy the file system into flash
cp.b 0xC0000000 0x60500000 $filesize

# Done!  Return to the Please Wait screen
mw.b 0x01C42000 0x41   #A
mw.b 0x01C42000 0x30   #0
mw.b 0x01C42000 0x36   #6
mw.b 0x01C42000 0x36   #6
mw.b 0x01C42000 0x67   #g
mw.b 0x01D0C000 0x41   #A
mw.b 0x01D0C000 0x30   #0
mw.b 0x01D0C000 0x36   #6
mw.b 0x01D0C000 0x36   #6
mw.b 0x01D0C000 0x67   #g

# Light up Status LED 1 and 2 to indicate
# completion.  This is a factory request
mw.w 0x01E260B8 0x0100
mw.w 0x01E260B8 0x0400
usb stop
```

### Analyzing update image

Mount ubifs using MTDRAM moudle

```bash
developer@ldc:~$ cd firmware/RM16AI_Rack_13731
developer@ldc:~$ sudo ./ubifs_mount.sh
```

will mount selected firmware to /media/cdrom folder. MTD/UBI/UBIFS parameters are the following 
```
[69824.966682] ubi0: default fastmap pool size: 10
[69824.966686] ubi0: default fastmap WL pool size: 5
[69824.966689] ubi0: attaching mtd0
[69824.966861] ubi0: scanning is finished
[69824.967051] ubi0: volume 0 ("rootfs") re-sized from 123 to 194 LEBs
[69824.967534] ubi0: attached mtd0 (name "mtdram test device", size 25 MiB)
[69824.967538] ubi0: PEB size: 131072 bytes (128 KiB), LEB size: 130944 bytes
[69824.967540] ubi0: min./max. I/O unit sizes: 1/64, sub-page size 1
[69824.967543] ubi0: VID header offset: 64 (aligned 64), data offset: 128
[69824.967545] ubi0: good PEBs: 200, bad PEBs: 0, corrupted PEBs: 0
[69824.967548] ubi0: user volume: 1, internal volumes: 1, max. volumes count: 128
[69824.967551] ubi0: max/mean erase counter: 1/1, WL threshold: 4096, image sequence number: 1606938876
[69824.967553] ubi0: available PEBs: 0, total reserved PEBs: 200, PEBs reserved for bad PEB handling: 0
[69824.967605] ubi0: background thread "ubi_bgt0d" started, PID 10957
```

Image analysis showed that there's ssh server dropbear, it is started in default runlevel, so we can gain SSH access to the mixer.

```
$ cat /etc/passwd
root:5sphjGCDWAh4Y:0:0:root:/home/root:/bin/sh
```
* no process respawn is configured inside `/etc/inittab`

`/etc/wpa_supplicant.conf`

* Wifi dongle is RTL8192CU

/etc/version
* [Arago 2011.06](http://arago-project.org/wiki/index.php/Setting_Up_Build_Environment)

```
$ cat /etc/fstab
# stock fstab - you probably want to override this with a machine specific one

rootfs               /                    auto       defaults,ro           1  1
proc                 /proc                proc       defaults              0  0
devpts               /dev/pts             devpts     mode=0620,gid=5       0  0
usbfs                /proc/bus/usb        usbfs      defaults,noauto       0  0
tmpfs                /var/volatile        tmpfs      defaults,size=4M      0  0
tmpfs                /dev/shm             tmpfs      mode=0777             0  0
tmpfs                /tmp                 tmpfs      defaults,size=8M      0  0
/dev/mtdblock3       /sfs                 jffs2      defaults,noexec       0  0
```

```
$ file /home/root/mixer
ELF 32-bit LSB executable, ARM, EABI4 version 1 (SYSV), dynamically linked, interpreter /lib/ld-, for GNU/Linux 2.6.16, not s
tripped
```

```
$ arm-linux-gnueabihf-readelf -d /home/root/mixer
Dynamic section at offset 0x4435b0 contains 29 entries:
  Tag        Type                         Name/Value
 0x00000001 (NEEDED)                     Shared library: [libstdc++.so.6]
 0x00000001 (NEEDED)                     Shared library: [libpthread.so.0]
 0x00000001 (NEEDED)                     Shared library: [librt.so.1]
 0x00000001 (NEEDED)                     Shared library: [libgcc_s.so.1]
 0x00000001 (NEEDED)                     Shared library: [libc.so.6]
 0x00000001 (NEEDED)                     Shared library: [libm.so.6]
 0x0000000c (INIT)                       0xa7a4
 0x0000000d (FINI)                       0x158760
 0x00000019 (INIT_ARRAY)                 0x453518
 0x0000001b (INIT_ARRAYSZ)               144 (bytes)
 0x0000001a (FINI_ARRAY)                 0x4535a8
 0x0000001c (FINI_ARRAYSZ)               4 (bytes)
 0x00000004 (HASH)                       0x8168
 0x00000005 (STRTAB)                     0x9528
 0x00000006 (SYMTAB)                     0x87d8
 0x0000000a (STRSZ)                      2450 (bytes)
 0x0000000b (SYMENT)                     16 (bytes)
 0x00000015 (DEBUG)                      0x0
 0x00000003 (PLTGOT)                     0x4536c0
 0x00000002 (PLTRELSZ)                   1592 (bytes)
 0x00000014 (PLTREL)                     REL
 0x00000017 (JMPREL)                     0xa16c
 0x00000011 (REL)                        0xa134
 0x00000012 (RELSZ)                      56 (bytes)
 0x00000013 (RELENT)                     8 (bytes)
 0x6ffffffe (VERNEED)                    0xa064
 0x6fffffff (VERNEEDNUM)                 6
 0x6ffffff0 (VERSYM)                     0x9eba
 0x00000000 (NULL)                       0x0
```

```
$ strings /home/root/mixer

...
/device.txt
DEVICE_NAME
Main: starting %s
rogue
beast
wolverine
wolverine_l
gambit
gambit_l
***** Error! Couldn't start because mixer name not recognized: %s
...
* STORM-NOAA Module                                      *
* BEAST-NOAA Module                                      *
* ROGUE-NOAA Module                                      *
* WOLVERINE-NOAA Module                                      *
* GAMBIT-NOAA Module                                      *
*  Product serial: 0x%0X                              *
* Firewire serial: 0x%0X                               *
*  Built with SDK Version: %02d.%02d.%02d                      *
*  Firmware Application Version: %02d.%02d.%02d, build %04d    *
*                       - built on %s, %s *
*                                                        *
*  FPGA Image loaded, Magic "%c%c%c%c"                       *
*        FPGA Revision: %02d.%02d.%02d, build %05d            *
*        Shelby Revision: %02d.%02d.%02d, build %05d          *
*  NO FPGA IMAGE FOUND                                   *
**********************************************************
* Target: xmen series module                             *
* Driver: DiceDriver    (Protocol Version: %02d.%02d.%02d.%02d)  *
* WARNING!  WARNING! WARNING! WARNING! WARNING! WARNING! *
* The FPGA Image is not compatible with this application *
* and the firmware will only provide functionality for   *
* loading the FPGA image through SPI or CLI.             *
* All audio and 1394 functionality is disabled.          *
error installing myApp cli tools
FPGA image is not valid
Error - unable to allocate buffer
Error reading FPGA image
...
StudioLive 16.4.2AI
{49B355DA-B613-40A0-9955-EAB6F6DEADD7}
N8Presonus5Mixer16RogueApplicationE
 !"#*+,-./89:;()<=&'
<=*+,-./01234567System_AuxPre1_Rogue
Channel_Info1_Rogue
...
StudioLive 24.4.2AI
{62BA428D-20C2-B56A-1367-65DCDCA5D997}
N8Presonus5Mixer16BeastApplicationE
 !"#
*+,-./012389:;()<=&'
<=*+,-./01234567
N8Presonus5Panel24BeastFrontPanelComponentE
...
StudioLive RM32 AI
StudioLive RML32 AI
N8Presonus5Mixer23WolverineRMLApplicationE
N8Presonus5Mixer20WolverineApplicationE
'& !"#-,+*10/.54329876<=:
&'<=*+,-./012345:
N8Presonus5Panel23WolverinePanelComponentE
rm32
N8Presonus5Mixer23WolverineMixerComponentE
N8Presonus5Panel23WolverinePanelRegistrarE
...
StudioLive RM16 AI
StudioLive RML16 AI
N8Presonus5Mixer20GambitRMLApplicationE
N8Presonus5Mixer17GambitApplicationE
-,+*10/.
&'<=*+,-./01:
N8Presonus5Panel20GambitPanelComponentE
rm16
N8Presonus5Mixer20GambitMixerComponentE
N8Presonus5Panel20GambitPanelRegistrarE
...
fpga
EVM Load FPGA
dump
rx=0,tx=1,rxdma=2,txdma=3
SPI Test
send
lm=0
band
all=100
Set a GEQ Band
setup
Setup a Geq
enable
EnableGeq
loot
loot
loot
loot
loot
loot
evm.fpga:
use: evm.fpga
------------------------------------------------------------
FPGA Load
spi.dump:
spi.dump:
use: spi.dump <item>
 <item>: rx, tx, rxdma, txdma
------------------------------------------------------------
SPI dump
spi.send:
use: spi.send <item>
 <item>: lm
------------------------------------------------------------
SPI send
geq.band:
use: geq.band <channel> <band> <step>
------------------------------------------------------------
<channel>       : 0-15, type all for all
<band>          : 0-30
<db>            : 0-127 64=0dB
geq.setup:
use: geq.setup <start> <end> <printmode>
------------------------------------------------------------
GEQ Setup
 <start>     : Smooth factor A1, 0-9 <end>       : Smooth factor A2, 0-9 <printmode> : verbosity, 0-2
geq.enable:
use: geq.enable <on/off>
------------------------------------------------------------
GEQ Setup
 <on.off>  : 0 or 1
DMA Status
 ctlr %08x stream %d chan %d
 vector %d stream->ccr %08x
 DMA   ISR:   %08x
 DMA %d CCR:   %08x
 DMA %d CNDTR: %08x
 DMA %d CPAR:  %08x
 DMA %d CMAR:  %08x
SPI Tx Dump
 put:     %i
 get:     %i
 orun:    %i
 toolong: %i
 cnt:     %i
 dmarun:  %s
   get:     %i
   put:     %i
   orun:    %i
   toolong: %i
   cnt:     %i
SPI Rx Dump
 DICE
2Long:0x%08X
Storm SPI
cm_reset
nvm_set_info: %d
nvm_store_info: %d
bad route rcvd:%.2X %.2X %.2X %.2X
Set I8S RX delay: %d
Set FPGA flags to: %d
GA:0x%08X 0x%08X
GEQ Enabled:%d
*** Assertion in %s, line %d  ***
shelbygeq.c
GEQ smoothing:0x%08X (%d) 0x%08X (%d) - 0x%08X
GQ %d
GEQ ch-len: %d %d %d
INCOMPLETE GEQ PACKET ERROR
= CLIPPED ch:%d band:%d gain:%d
= ch:%d band:%d gain:%d
geqBusyWait: %d
=SwapBuf addr=0x%08x en=0x%08x, enflip=0x%08x
=GEQ BufID=%d (0x%08x)
@***mutedlinks
***enabledlinks
StudioLive
Unused\Unused\Unused\Unused\Unused\Unused\Unused\Unused\Unused\Unused\Unused\Unused\Internal\\
CH1\CH2\CH3\CH4\CH5\CH6\CH7\CH8\CH9\CH10\CH11\CH12\CH13\CH14\CH15\CH16\CH17\CH18\CH19\CH20\CH21\CH22\CH23\CH24\CH25\CH26\CH27\CH28\CH29\CH30\CH31\CH32\AUX1\AUX2\AUX3\AUX4\AUX5\AUX6\AUX7\AUX8\AUX9\AUX10\AUX11\AUX12\AUX13\AUX14\AUX15\AUX16\\
CH1\CH2\CH3\CH4\CH5\CH6\CH7\CH8\CH9\CH10\CH11\CH12\CH13\CH14\CH15\CH16\CH17\CH18\CH19\CH20\CH21\CH22\CH23\CH24\CH25\CH26\CH27\CH28\CH29\CH30\CH31\CH32\2TrackL\2TrackR\\
CH1\CH2\CH3\CH4\CH5\CH6\CH7\CH8\CH9\CH10\CH11\CH12\CH13\CH14\CH15\CH16\CH17\CH18\CH19\CH20\CH21\CH22\CH23\CH24\AUX1\AUX2\AUX3\AUX4\AUX5\AUX6\AUX7\AUX8\AUX9\AUX10\AUX11\AUX12\AUX13\AUX14\AUX15\AUX16\\
CH1\CH2\CH3\CH4\CH5\CH6\CH7\CH8\CH9\CH10\CH11\CH12\CH13\CH14\CH15\CH16\CH17\CH18\CH19\CH20\CH21\CH22\CH23\CH24\2TrackL\2TrackR\\
CH1\CH2\CH3\CH4\CH5\CH6\CH7\CH8\CH9\CH10\CH11\CH12\CH13\CH14\CH15\CH16\AUX1\AUX2\AUX3\AUX4\AUX5\AUX6\AUX7\AUX8\AUX9\AUX10\AUX11\AUX12\AUX13\AUX14\AUX15\AUX16\\
CH1\CH2\CH3\CH4\CH5\CH6\CH7\CH8\CH9\CH10\CH11\CH12\CH13\CH14\CH15\CH16\2TrackL\2TrackR\\
CH1\CH2\CH3\CH4\CH5\CH6\CH7\CH8\CH9\CH10\CH11\CH12\CH13\CH14\CH15\CH16\CH17\CH18\CH19\CH20\CH21\CH22\CH23\CH24\CH25\CH26\CH27\CH28\CH29\CH30\CH31\CH32\AUX1\AUX2\AUX3\AUX4\AUX5\AUX6\AUX7\AUX8\AUX9\AUX10\AUX11\AUX12\AUX13\AUX14\AUX15\AUX16\AUX17\AUX18\AUX19\AUX20\\
...
nvm.c
error installing NVM cli tools
Flash Device #%i
  Start:  0x%08x
  End:    0x%08x
  Block  size  nbblocks
  %-7i%-6i%i
NVM info Block
  MAC:     %02x:%02x:%02x:%02x:%02x:%02x
  Product:  %i
  SerialNo: %i
NVM FPGA Block
  Name:     %-32s
  Version:  %i.%i.%i.%i
  Size:     %i
  INVALID IMAGE
Erase NVM FPGA image... (takes a while)
Error -Erasing Image
Error -Unable to open com port
start XModem-1k transfer ...
Error open xyzModem: %s
Flash Program error
Loaded %i bytes
XModem Error: %s
Illegal MAC address
list
List of NVM devices
Set Non Volatile Mem.
info
Non Volatile Mem. Info
Erase Non Volatile Mem. FPGA Image
load
Load FPGA Image using XModem-1k
loot
loot
loot
loot
loot
list:
use: nvm.list
------------------------------------------------------------
List of NVM devices
set:
use: nvm.set <mac_adr> <prodID> <serial>
 <mac_adr> : xx-xx-xx-xx-xx-xx
 <prodID>  : Integer product identifier
 <serial>  : Integer serial number
------------------------------------------------------------
Set Non Volatile Mem.
info:
use: nvm.info
------------------------------------------------------------
Non Volatile Mem. Info
erase:
use: nvm.erase
------------------------------------------------------------
Erase Non Volatile Mem. FPGA Image
load:
use: nvm.load <ver> <image name>.
  <ver>:         32 bit version (maj:8,min:4,sub:4,build:16)
  <image name> : name (enclose in  if it contains spaces
------------------------------------------------------------
Load FPGA Image using XModem-1k
Error, FPGA no init_b
Error, FPGA not ready
error installing TCKernel cli tools
...
StudioLive RM16 AI
StudioLive RML16 AI
N8Presonus5Mixer20GambitRMLApplicationE
N8Presonus5Mixer17GambitApplicationE
-,+*10/.
&'<=*+,-./01:
N8Presonus5Panel20GambitPanelComponentE
rm16
N8Presonus5Mixer20GambitMixerComponentE
N8Presonus5Panel20GambitPanelRegistrarE
...

/sfs/hwaddr.txt
%llx
speaker
%s shutting down DSP
UC network manager startup failed!
%llu
GUID CALC: %s
%s local ip address: %s
Do not power off mixer
IOCARD ARM upgrade
IO CARD NOT FOUND
Please check your IO Card slot
IOCARD FPGA upgrade
IO Card Updated
Mixer starting...
IO CARD UPDATE FAILED
Please power cycle mixer
IO Card product type reprogrammed
 App:
N8Presonus5Mixer16MixerApplicationE
storm_top.bin
```

`/lib/modules`
* Kernel 2.6.37

`/lib/modules/2.6.37+/kernel/fs/nfs`
* theoretically we can boot from NFS

