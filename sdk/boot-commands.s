usb start;fatload usb 0:1 0xC0000000 linux-5.img;source 0xC0000000

setenv bootargs mem=96M console=ttyS2,115200n8 noinitrd root=/dev/nfs nfsroot=192.168.11.10:root ip=192.168.11.20:192.168.11.10:192.168.11.1:255.255.255.0:presonus::off;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000	

setenv bootargs debug earlyprintk mem=96M console=ttyS2,115200n8 noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync lpj=1134592 printk.synchronous=1;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000


setenv bootargs earlyprintk mem=96M console=ttyS2,115200n8 noinitrd ubi.mtd=rootfs rootfstype=ubifs root=ubi0:rootfs rootflags=sync lpj=1134592 printk.synchronous=1;usb start;fatload usb 0:1 0xC2000000 uImage.da850-presonus;bootm 0xC2000000
