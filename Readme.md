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

This is the rootfs image, with JFFS2 fs type. We'll examine it's contents later

### `upgrade.bin`

Looks like a custom container for upgrade items. Quick look showed that is contains a set of files, including unstripped ELF.

### Contents of `initvars.scr`

This script seems to be started first and pass control to `recovery.scr` or flash update by itself.

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

This is the main update script, that flashes new update into internal NAND flash

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

### Analyzing JFFS2 update image

Mount jffs using MTDRAM moudle

```bash
developer@ldc:~$ sudo ./jffs2_mount_mtdram.sh rootfs.jffs2 /mnt/jffs2 256
```

```bash
developer@ldc:~$ sudo ./jffs2_mount_loop.sh rootfs.jffs2 /mnt/jffs2 256
```