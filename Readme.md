# Digging Presonus RML16AI + CS18AI

Presonus has deprecated ther RM/RML series mixer. That mostly means that support for this great piece of hardware is dropped too. 
Last firmware update has been released on Sep, 13th 2018 under the version of v13731. It brings some improvements and features, but still has some issues.

I've reported that issues to presonus in Dec 2018-Jan 2019, but no fixes was released up to date. Well, I've decided to take a look into it by myself.

## Disclaimer

This repository is for educational purposses only. I'm not responsible if any damage is done to your mixer 

## List of terms

* `Gambit` - Presonus RM16AI
* `Gambit_l` - Presonus RML16AI
* `Rogue` - StudioLive 16.4.2AI
* `Beast`- StudioLive 24.4.2AI
* `Wolverine` - StudioLive RM32 AI
* `Wolverine_l` - StudioLive RML32 AI
* `XMEN` - AVB extension card
* `console` - CS18AI

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

## Tools needed

```
$ apt install u-boot-tools mtd-utils binwalk gcc-5-arm-linux-gnueabihf g++-5-arm-linux-gnueabihf
```

### `uImage`

This is U-Boot linux Kernel image. It is directly used to boot the mixer during factory reset process. This is also seems to be the kernel that is flashed as upgrade

```
$ dumpimage -l uImage
Image Name:   Linux-2.6.37+
Created:      Fri Mar  2 00:22:24 2018
Image Type:   ARM Linux Kernel Image (uncompressed)
Data Size:    3437312 Bytes = 3356.75 kB = 3.28 MB
Load Address: c0008000
Entry Point:  c0008000
```

Dumping kernel to `vmlinux` file

```
$ dumpimage -i uImage image-bin
 ```

keywords `presonus` `audio` `davinci` `pcm` `omap`
```
$ strings image-bin | less 

<4>omapl138_presonus_init: emac registration failed: %d
ttyS
115200
<4>omapl138_presonus_init: edma registration failed: %d
<4>omapl138_presonus_init: watchdog registration failed: %d
<4>omapl138_presonus_init: lcdc registration failed: %d
<4>omapl138_presonus_init: cpuidle registration failed: %d
<4>omapl138_presonus_init: suspend registration failed: %d```

Presonus OMAP-L138 Platform
...
davinci-pcm-audio
davinci-mcbsp
spi_davinci
cpuidle-davinci
omap_rtc
davinci_mmc
da8xx_lcdc
davinci-mcasp
davinci_mdio
davinci_emac
i2c_davinci
...
davinci_emac_probe
TI DaVinci EMAC Linux v6.1
davinci_emac.debug_level
...
<4>%s: Unable to map DDR2 controller
arch/arm/mach-davinci/devices-da8xx.c
serial8250
davinci-pcm-audio
davinci-mcbsp
spi_davinci
cpuidle-davinci
omap_rtc
davinci_mmc
da8xx_lcdc
davinci-mcasp
davinci_mdio
davinci_emac
i2c_davinci
...
```

## TTYs on CS18AI

ttyS0 - SysEx to DICE
ttyS1 - FP interface
ttyS2 - Debug interface (uBoot + linux console)

#### Kernel startup output

captured from [here][16]

```
Linux version 2.6.37+ (bob@ubuntu) (gcc version 4.3.3 (GCC) ) #819 PREEMPT Tue Jul 26 12:03:50 CDT 2016
CPU: ARM926EJ-S [41069265] revision 5 (ARMv5TEJ), cr=00053177
CPU: VIVT data cache, VIVT instruction cache
Machine: Presonus OMAP-L138 Platform
Memory policy: ECC disabled, Data cache writeback
DaVinci da850/omap-l138/am18x variant 0x1
On node 0 totalpages: 24576
free_area_init_node: node 0, pgdat c034e6c0, node_mem_map c0360000
  DMA zone: 192 pages used for memmap
  DMA zone: 0 pages reserved
  DMA zone: 24384 pages, LIFO batch:3
pcpu-alloc: s0 r0 d32768 u32768 alloc=1*32768
pcpu-alloc: [0] 0 
Built 1 zonelists in Zone order, mobility grouping on.  Total pages: 24384
Kernel command line: mem=96M console=ttyS2,115200n8 noinitrd ubi.mtd=2 rootfstype=ubifs root=ubi0:rootfs rootflags=sync lpj=1134592 quiet
PID hash table entries: 512 (order: -1, 2048 bytes)
Dentry cache hash table entries: 16384 (order: 4, 65536 bytes)
Inode-cache hash table entries: 8192 (order: 3, 32768 bytes)
Memory: 96MB = 96MB total
Memory: 93940k/93940k available, 4364k reserved, 0K highmem
Virtual kernel memory layout:
    vector  : 0xffff0000 - 0xffff1000   (   4 kB)
    fixmap  : 0xfff00000 - 0xfffe0000   ( 896 kB)
    DMA     : 0xff000000 - 0xffe00000   (  14 MB)
    vmalloc : 0xc6800000 - 0xfea00000   ( 898 MB)
    lowmem  : 0xc0000000 - 0xc6000000   (  96 MB)
    modules : 0xbf000000 - 0xc0000000   (  16 MB)
      .init : 0xc0008000 - 0xc0025000   ( 116 kB)
      .text : 0xc0025000 - 0xc032e000   (3108 kB)
      .data : 0xc032e000 - 0xc034f300   ( 133 kB)
SLUB: Genslabs=13, HWalign=32, Order=0-3, MinObjects=0, CPUs=1, Nodes=1
Preemptable hierarchical RCU implementation.
   RCU-based detection of stalled CPUs is disabled.
   Verbose stalled-CPUs detection is disabled.
NR_IRQS:245
Console: colour dummy device 80x30
Calibrating delay loop (skipped) preset value.. 226.91 BogoMIPS (lpj=1134592)
pid_max: default: 32768 minimum: 301
Mount-cache hash table entries: 512
CPU: Testing write buffer coherency: ok
DaVinci: 144 gpio irqs
regulator: core version 0.5
regulator: dummy: 
NET: Registered protocol family 16
bio: create slab <bio-0> at 0
SCSI subsystem initialized
usbcore: registered new interface driver usbfs
usbcore: registered new interface driver hub
usbcore: registered new device driver usb
Switching to clocksource timer0_1
musb-hdrc: version 6.0, host, debug=0
musb-hdrc musb-hdrc: dma type: dma-cppi41
Waiting for USB PHY clock good...
musb-hdrc: ConfigData=0x06 (UTMI-8, dyn FIFOs, SoftConn)
musb-hdrc: MHDRC RTL version 1.800 
musb-hdrc: setup fifo_mode 2
musb-hdrc: 9/9 max ep, 4032/4096 memory
musb-hdrc musb-hdrc: MUSB HDRC host driver
musb-hdrc musb-hdrc: new USB bus registered, assigned bus number 1
hub 1-0:1.0: USB hub found
hub 1-0:1.0: 1 port detected
musb-hdrc musb-hdrc: USB Host mode controller at fee00000 using DMA, IRQ 58
NET: Registered protocol family 2
IP route cache hash table entries: 1024 (order: 0, 4096 bytes)
TCP established hash table entries: 4096 (order: 3, 32768 bytes)
TCP bind hash table entries: 4096 (order: 2, 16384 bytes)
TCP: Hash tables configured (established 4096 bind 4096)
TCP reno registered
UDP hash table entries: 256 (order: 0, 4096 bytes)
UDP-Lite hash table entries: 256 (order: 0, 4096 bytes)
NET: Registered protocol family 1
EMAC: RMII PHY configured, MII PHY will not be functional
JFFS2 version 2.2. (NAND) © 2001-2006 Red Hat, Inc.
msgmni has been set to 183
io scheduler noop registered (default)
Serial: 8250/16550 driver, 3 ports, IRQ sharing disabled
serial8250.0: ttyS0 at MMIO 0x1c42000 (irq = 25) is a AR7
serial8250.0: ttyS1 at MMIO 0x1d0c000 (irq = 53) is a AR7
serial8250.0: ttyS2 at MMIO 0x1d0d000 (irq = 61) is a AR7
console [ttyS2] enabled
physmap platform flash device: 02000000 at 60000000
physmap-flash.0: Found 1 x16 devices at 0x0 in 16-bit bank. Manufacturer ID 0x0000c2 Chip ID 0x00227e
Amd/Fujitsu Extended Query Table at 0x0040
  Amd/Fujitsu Extended Query version 1.3.
number of CFI chips: 1
cmdlinepart partition parsing not available
RedBoot partition parsing not available
Using physmap partition information
Creating 4 MTD partitions on "physmap-flash.0":
0x000000000000-0x0000000a0000 : "UBL/U-Boot"
0x0000000a0000-0x000000500000 : "kernel"
0x000000500000-0x000001c00000 : "rootfs"
0x000001c00000-0x000002000000 : "settings"
UBI: attaching mtd2 to ubi0
UBI: physical eraseblock size:   131072 bytes (128 KiB)
UBI: logical eraseblock size:    130944 bytes
UBI: smallest flash I/O unit:    1
UBI: VID header offset:          64 (aligned 64)
UBI: data offset:                128
UBI: max. sequence number:       0
UBI: volume 0 ("rootfs") re-sized from 122 to 180 LEBs
UBI: attached mtd2 to ubi0
UBI: MTD device name:            "rootfs"
UBI: MTD device size:            23 MiB
UBI: number of good PEBs:        184
UBI: number of bad PEBs:         0
UBI: number of corrupted PEBs:   0
UBI: max. allowed volumes:       128
UBI: wear-leveling threshold:    4096
UBI: number of internal volumes: 1
UBI: number of user volumes:     1
UBI: available PEBs:             0
UBI: total number of reserved PEBs: 184
UBI: number of PEBs reserved for bad PEB handling: 0
UBI: max/mean erase counter: 1/0
UBI: image sequence number:  860712550
spi_davinci spi_davinci.1: DMA: supported
spi_davinci spi_davinci.1: DMA: RX channel: 18, TX channel: 19, event queue: 0
UBI: background thread "ubi_bgt0d" started, PID 360
spi_davinci spi_davinci.1: Controller at 0xfef0e000
spi_davinci spi_davinci.0: DMA: supported
spi_davinci spi_davinci.0: DMA: RX channel: 14, TX channel: 15, event queue: 0
spi_davinci spi_davinci.0: Controller at 0xfec41000
davinci_mdio davinci_mdio.0: davinci mdio revision 1.5
davinci_mdio davinci_mdio.0: no live phy, scanning all
davinci_mdio: probe of davinci_mdio.0 failed with error -5
watchdog watchdog: heartbeat 60 sec
cpuidle: using governor ladder
cpuidle: using governor menu
TCP cubic registered
NET: Registered protocol family 17
Registering the dns_resolver key type
davinci_emac_probe: using random MAC addr: ba:6d:5f:09:0e:4b
UBIFS: parse sync
UBIFS: mounted UBI device 0, volume 0, name "rootfs"
UBIFS: file system size:   22260480 bytes (21738 KiB, 21 MiB, 170 LEBs)
UBIFS: journal size:       3404544 bytes (3324 KiB, 3 MiB, 26 LEBs)
UBIFS: media format:       w4/r0 (latest is w4/r0)
UBIFS: default compressor: lzo
UBIFS: reserved for root:  0 bytes (0 KiB)
VFS: Mounted root (ubifs filesystem) on device 0:11.
udevd (460): /proc/460/oom_adj is deprecated, please use /proc/460/oom_score_adj instead.
Running do_deferred_initcalls()
ohci_hcd: USB 1.1 'Open' Host Controller (OHCI) Driver
ohci ohci.0: DA8xx OHCI
ohci ohci.0: new USB bus registered, assigned bus number 2
Waiting for USB PHY clock good...
ohci ohci.0: irq 59, io mem 0x01e25000
hub 2-0:1.0: USB hub found
hub 2-0:1.0: 1 port detected
Initializing USB Mass Storage driver...
usbcore: registered new interface driver usb-storage
USB Mass Storage support registered.
Freeing init memory: 116K
net eth0: no phy, defaulting to 100/full
net eth0: DaVinci EMAC: ioctl not supported
hrtimer: interrupt took 125959 ns
net eth0: DaVinci EMAC: ioctl not supported
usb 1-1: new high speed USB device using musb-hdrc and address 2
rtw driver version=v3.4.4_4749.20121105 
Build at: Jul 26 2016 12:04:26
register rtw_netdev_ops to netdev_ops
CHIP TYPE: RTL8188C_8192C

usb_endpoint_descriptor(0):
bLength=7
bDescriptorType=5
bEndpointAddress=81
wMaxPacketSize=200
bInterval=0
RT_usb_endpoint_is_bulk_in = 1

usb_endpoint_descriptor(1):
bLength=7
bDescriptorType=5
bEndpointAddress=2
wMaxPacketSize=200
bInterval=0
RT_usb_endpoint_is_bulk_out = 2

usb_endpoint_descriptor(2):
bLength=7
bDescriptorType=5
bEndpointAddress=3
wMaxPacketSize=200
bInterval=0
RT_usb_endpoint_is_bulk_out = 3

usb_endpoint_descriptor(3):
bLength=7
bDescriptorType=5
bEndpointAddress=84
wMaxPacketSize=40
bInterval=1
RT_usb_endpoint_is_int_in = 4, Interval = 1
nr_endpoint=4, in_num=2, out_num=2

USB_SPEED_HIGH
Chip Version ID: VERSION_NORMAL_TSMC_CHIP_88C.
RF_Type is 3!!
EEPROM type is E-FUSE
====> ReadAdapterInfo8192C
Boot from EFUSE, Autoload OK !
EEPROMVID = 0x0bda
EEPROMPID = 0x8176
EEPROMCustomerID : 0x00
EEPROMSubCustomerID: 0x00
RT_CustomerID: 0x00
_ReadMACAddress MAC Address from EFUSE = 5c:f3:70:21:61:06
EEPROMRegulatory = 0x0
_ReadBoardType(0)
BT Coexistance = disable
RT_ChannelPlan: 0x00
_ReadPSSetting...bHWPwrPindetect(0)-bHWPowerdown(0) ,bSupportRemoteWakeup(0)
### PS params=>  power_mgnt(0),usbss_enable(0) ###
### AntDivCfg(0)
readAdapterInfo_8192CU(): REPLACEMENT = 1
<==== ReadAdapterInfo8192C in 700 ms
rtw_macaddr_cfg MAC Address  = 5c:f3:70:21:61:06
MAC Address from pnetdev->dev_addr= 5c:f3:70:21:61:06
bDriverStopped:1, bSurpriseRemoved:0, bup:0, hw_init_completed:0
usbcore: registered new interface driver rtl8192cu
net eth0: DaVinci EMAC: ioctl not supported
usb 1-1: USB disconnect, address 2
+rtw_dev_remove
rtw_sta_flush
<=== rtw_dev_unload
+r871xu_dev_remove, hw_init_completed=0
free_recv_skb_queue not empty, 8
=====> rtl8192c_free_hal_data =====
<===== rtl8192c_free_hal_data =====
-r871xu_dev_remove, done
usb 1-1: new high speed USB device using musb-hdrc and address 3
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
usb 1-1: USB disconnect, address 3
usb 1-1: new high speed USB device using musb-hdrc and address 4
register rtw_netdev_ops to netdev_ops
CHIP TYPE: RTL8188C_8192C

usb_endpoint_descriptor(0):
bLength=7
bDescriptorType=5
bEndpointAddress=81
wMaxPacketSize=200
bInterval=0
RT_usb_endpoint_is_bulk_in = 1

usb_endpoint_descriptor(1):
bLength=7
bDescriptorType=5
bEndpointAddress=2
wMaxPacketSize=200
bInterval=0
RT_usb_endpoint_is_bulk_out = 2

usb_endpoint_descriptor(2):
bLength=7
bDescriptorType=5
bEndpointAddress=3
wMaxPacketSize=200
bInterval=0
RT_usb_endpoint_is_bulk_out = 3

usb_endpoint_descriptor(3):
bLength=7
bDescriptorType=5
bEndpointAddress=84
wMaxPacketSize=40
bInterval=1
RT_usb_endpoint_is_int_in = 4, Interval = 1
nr_endpoint=4, in_num=2, out_num=2

USB_SPEED_HIGH
Chip Version ID: VERSION_NORMAL_TSMC_CHIP_88C.
RF_Type is 3!!
EEPROM type is E-FUSE
====> ReadAdapterInfo8192C
Boot from EFUSE, Autoload OK !
EEPROMVID = 0x0bda
EEPROMPID = 0x8176
EEPROMCustomerID : 0x00
EEPROMSubCustomerID: 0x00
RT_CustomerID: 0x00
_ReadMACAddress MAC Address from EFUSE = 5c:f3:70:21:61:06
EEPROMRegulatory = 0x0
_ReadBoardType(0)
BT Coexistance = disable
RT_ChannelPlan: 0x00
_ReadPSSetting...bHWPwrPindetect(0)-bHWPowerdown(0) ,bSupportRemoteWakeup(0)
### PS params=>  power_mgnt(0),usbss_enable(0) ###
### AntDivCfg(0)
readAdapterInfo_8192CU(): REPLACEMENT = 1
<==== ReadAdapterInfo8192C in 710 ms
rtw_macaddr_cfg MAC Address  = 5c:f3:70:21:61:06
MAC Address from pnetdev->dev_addr= 5c:f3:70:21:61:06
bDriverStopped:1, bSurpriseRemoved:0, bup:0, hw_init_completed:0
net eth0: DaVinci EMAC: ioctl not supported
net eth0: DaVinci EMAC: ioctl not supported
usb 1-1: USB disconnect, address 4
+rtw_dev_remove
rtw_sta_flush
<=== rtw_dev_unload
+r871xu_dev_remove, hw_init_completed=0
free_recv_skb_queue not empty, 8
=====> rtl8192c_free_hal_data =====
<===== rtl8192c_free_hal_data =====
-r871xu_dev_remove, done
usb 1-1: new high speed USB device using musb-hdrc and address 5
usb 1-1: USB disconnect, address 5
usb 1-1: new high speed USB device using musb-hdrc and address 6
```

### `rootfs.img`

This is raw rootfs UBIFS image. We'll examine it's contents later

### `upgrade.bin`

tar.gz with unstripped ELF mixer binary and MD5 sum file. Can be extracted with

```
$ tar xzf upgrade.bin
```

### Contents of `initvars.scr`

This is U-Boot script image. This script seems to be started first and pass control to `recovery.scr` or flash update by itself.

this file is compiled with `mkimage` tool. See example [here][17]


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
developer@ldc:~$ sudo ./scripts/ubifs_mount.sh firmware/RM16AI_Rack_13731/rootfs.img
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

UBI version:                    1
Count of UBI devices:           1
UBI control device major/minor: 10:55
Present UBI devices:            ubi0

ubi0
Volumes count:                           1
Logical eraseblock size:                 130944 bytes, 127.9 KiB
Total amount of logical eraseblocks:     200 (26188800 bytes, 25.0 MiB)
Amount of available logical eraseblocks: 0 (0 bytes)
Maximum count of volumes                 128
Count of bad physical eraseblocks:       0
Count of reserved physical eraseblocks:  0
Current maximum erase counter value:     2
Minimum input/output unit size:          1 byte
Character device major/minor:            244:0
Present volumes:                         0

Volume ID:   0 (on ubi0)
Type:        dynamic
Alignment:   1
Size:        194 LEBs (25403136 bytes, 24.2 MiB)
State:       OK
Name:        rootfs
Character device major/minor: 244:1



Image analysis showed that there's ssh server dropbear, it is started in default runlevel, so we can gain SSH access to the mixer.

```
$ cat /etc/passwd
root:5sphjGCDWAh4Y:0:0:root:/home/root:/bin/sh
```
* no process respawn is configured inside `/etc/inittab`

`/etc/wpa_supplicant.conf`

* Wifi dongle is RTL8192CU

/etc/version
* [Arago 2011.06][18]

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

## Components firmware

For `CS18AI`

* Dice3 firmware binary is placed in `dice3_surface_code` symbol. Head search pattern: `\x54\x43\x41\x54\x03\x31\x64\x03` Tail search pattern: `\x4D\x0E\x9C\x4F\x00\x00\x00\x00`
* Surface (LPC) firmware binary is placed in `panel_surface_code` symbol. Head search pattern: `\x00\x20\x00\x10\x27\x01\x00\x00` Tail search pattern: unknown


## Reflashing RML16AI to RML32AI

This procedure can be easily done via [StudioLive RM series Firmware Recovery - Factory Reset][19]

## Gaining SSH Access to target

`dropbear` is configured to connect with 

```
ssh -oCiphers=aes128-cbc -oKexAlgorithms=+diffie-hellman-group1-sha1 root@192.168.1.11
```

but we do not have root password.

Typically, Linux hashes passwords and stores them in `/etc/shadow`. But this system has huge security flaws: 
* Passwords are stored in `/etc/passwd` with old [DES encryption algorythm][20]
* We can flash any image on the target via [Factory Reset][19]. So it is easily to set default known hash by replacing `/etc/default/passwd`, rather than knowing original password.

Let's analyze the strenght of password with [JohnTheRipper][21].

```
sudo apt install john
sudo john <mounted-image-path>/etc/passwd -show
```

this will run default dictionary over the hash and literally in a second will give us a result.
```
root:demands:0:0:root:/home/root:/bin/sh
```

So, `root` password to the system is really weak.

## Dumping NOR image from u-boot

* capture output from the following comand
```
md.b 60000000 2000000
```

* remove extra lines from dump file

* convert hex dump to binary with

```
xxd -r -seek -0x60000000 flash.dump flash.bin
```

* Extracting partitions

```
dd if=flash.bin of=./u-boot-ais.bin bs=1 count=655360
dd if=flash.bin of=./uImage.bin bs=1 skip=655360 count=4587520
dd if=flash.bin of=./rootfs.bin bs=1 skip=5242880 count=24117248
dd if=flash.bin of=./sfs.bin bs=1 skip=29360128
```

## Flash manipulations

Reflash sfs

```
erase 0x61C00000 0x61FFFFFF
loady 0xC2000000
cp.b  0xC2000000 0x61C00000 $filesize
```

### Strace digging

* `strace ./surface 2>&1 | grep -v clock_gettime | grep -v 'read(3, "",' | grep -v 'write(3, "3000g", 5)'`
* `strace ./surface 2>&1 | grep -v clock_gettime | grep -v 'read(3, "",' | grep -v 'write(3, "3000g", 5)' | grep -v 'write(3, "3001g", 5)'`

## Links and references

[1]: http://wiki.emacinc.com/wiki/Mounting_JFFS2_Images_on_a_Linux_PC
[2]: http://www.linux-mtd.infradead.org/faq/ubifs.html
[3]: http://www.linux-mtd.infradead.org/doc/ubi.html#L_min_io_unit
[4]: https://pjankows.blogspot.com/2012/01/how-to-mount-ubi-image.html
[5]: http://www.linux-mtd.infradead.org/faq/nand.html
[6]: https://unix.stackexchange.com/questions/428238/how-can-i-change-a-single-file-from-an-ubi-image
[7]: https://elinux.org/UBIFS
[8]: http://dmilvdv.narod.ru/Translate/ELSDD/elsdd_mtdutils_package.html
[9]: http://software-dl.ti.com/processor-sdk-linux/esd/docs/latest/linux/Foundational_Components_U-Boot.html#nand
[10]: https://training.ti.com/restoring-and-updating-u-boot-nand-omap-l138
[11]: http://processors.wiki.ti.com/index.php/Boot_Images_for_OMAP-L138
[12]: https://reverseengineering.stackexchange.com/questions/60/is-reverse-engineering-and-using-parts-of-a-closed-source-application-legal?newreg=21b9c4f8a77a486ca38fdc2df38e1264
[13]: http://processors.wiki.ti.com/index.php/Linux_Core_U-Boot_User%27s_Guide#Using_NAND
[14]: http://processors.wiki.ti.com/index.php/Booting_Linux_kernel_using_U-Boot#NOR_Flash
[15]: http://processors.wiki.ti.com/index.php/Building_03.22_PSP_release_Components_for_OMAP-L138#Building_uImage
[16]: https://forums.presonus.com/viewtopic.php?f=222&p=176954&sid=b66b0e05156810e02d0fdb6405a78598
[17]: https://www.denx.de/wiki/view/DULG/UBootScripts
[18]: http://arago-project.org/wiki/index.php/Setting_Up_Build_Environment
[19]: https://support.presonus.com/hc/en-us/articles/210047563-StudioLive-RM-series-Firmware-Recovery-Factory-Reset
[20]: https://www.win.tue.nl/~aeb/linux/hh/hh-4.html
[21]: https://linuxconfig.org/password-cracking-with-john-the-ripper-on-linux
