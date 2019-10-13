setenv bootargs_norfs 'mem=32M console=ttyS2,115200n8 root=/dev/mtdblock2 rootfstype=jffs2 ip=off quiet'
setenv bootcmd_norfs 'setenv bootargs ${bootargs_norfs};bootm 0x600A0000'
setenv bootcmd_fullrecovery 'usb start;if fatload usb 0:1 0xC0000000 recovery.scr;then source 0xC0000000;else run bootcmd_norfs;fi'
setenv bootcmd 'run bootcmd_fullrecovery'
