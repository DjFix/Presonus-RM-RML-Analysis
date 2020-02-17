uboot options?

MV88E61XX_SWITCH
MV88E6352_SWITCH

usb start;fatload usb 0:1 0xC0000000 linux-5.img;source 0xC0000000

usb start;fatload usb 0:1 0xC0000000 recovery.scr;source 0xC0000000	

## Local boot experiments
	setenv bootargs debug earlyprintk noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync rw;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000
	setenv bootargs earlyprintk noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync rw;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000
	setenv bootargs earlyprintk noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync rw init=/bin/sh;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000


## NFS boot experiments
	setenv bootargs console=ttyS2,115200n8 root=/dev/nfs rdinit=/nonsense rootfstype=nfs nfsroot=212.116.109.58:/,vers=4,tcp rootwait rw ip=dhcp;usb start;fatload usb 0:1 0xC2000000 uImage.presonus-cs18ai;bootm 0xC2000000

## loopfs experiments
	# works fine with initramfs
	setenv bootargs console=ttyS2,115200n8 root=sda1 loop=rootfs.squashfs; usb start; fatload usb 0:1 0xC2000000 uImage.presonus-cs18ai; bootm 0xC2000000

run bootcmd_recovery

mkdir --parents {bin,dev,etc,lib,lib64,mnt/root,proc,root,sbin,sys}
cp --archive /dev/{null,console,tty,sda1} dev/


mkdir -p /loop && mount /mnt/root/rootfs.squashfs /loop

exec switch_root -c /dev/console /loop /sbin/init