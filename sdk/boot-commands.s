uboot options?

MV88E61XX_SWITCH
MV88E6352_SWITCH

usb start;fatload usb 0:1 0xC0000000 linux-5.img;source 0xC0000000

usb start;fatload usb 0:1 0xC0000000 recovery.scr;source 0xC0000000

setenv bootargs noinitrd root=/dev/nfs nfsroot=192.168.11.10:root ip=192.168.11.20:192.168.11.10:192.168.11.1:255.255.255.0:presonus::off;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000	

setenv bootargs debug earlyprintk noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync rw;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000

setenv bootargs earlyprintk noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync rw;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000

setenv bootargs earlyprintk noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync rw init=/bin/sh;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000
