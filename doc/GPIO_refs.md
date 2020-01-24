
# Pin controls

## GPIO Base


System registers `gpiochip0`. Offset of the pin should be added to `0`

## Main LCD Brightness only???

* 0x61 (offs: `127`) -  Discovered accidently. May harm
** `0` - Lower brightness
** `1` - Higher brightness
to test:

```bash
GPIO_BASE=0
```

```bash
PIN=$(($GPIO_BASE+127))
echo $PIN > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio$PIN/direction
echo 1 > /sys/class/gpio/gpio$PIN/value
sleep 1
echo 0 > /sys/class/gpio/gpio$PIN/value
sleep 1
echo in > /sys/class/gpio/gpio$PIN/direction

```

## Main LCD + scribble strip Brightness

* 0x61 (offs: `97`) - Main LCD + scribble strip Brightness
** `0` - Lower brightness
** `1` - Higher brightness


to test:

```bash
PIN=$(($GPIO_BASE+97))
echo $PIN > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio$PIN/direction
echo 1 > /sys/class/gpio/gpio$PIN/value
sleep 1
echo 0 > /sys/class/gpio/gpio$PIN/value
sleep 1
echo in > /sys/class/gpio/gpio$PIN/direction

```

Deduced from this
```cpp
void method.Presonus::Surface::SurfaceRootComponent.paramChangedLcdBrightness_Core::Portable::Parameter(int32_t arg2)
{
    int32_t arg1;
    undefined4 c;
    undefined4 unaff_r5;
    undefined4 unaff_r11;
    int32_t in_lr;
    int32_t var_24h;
    
    arg1 = (**(code **)(*(int32_t *)arg2 + 0x44))(arg2);
    c = sym.__fixsfsi(arg1);
    *(undefined4 *)(in_lr + -4) = 0xa4c64;
    *(undefined4 *)(in_lr + -8) = 0xad264;
    *(int32_t *)(in_lr + -0xc) = in_lr;
    *(BADSPACEBASE **)(in_lr + -0x10) = *(undefined **)0x54;
    *(undefined4 *)(in_lr + -0x14) = unaff_r5;
    *(undefined4 *)(in_lr + -0x18) = unaff_r11;
    arg1 = in_lr + -0x28;
    sym.Presonus::Panel::OutputPin::OutputPin_int(arg1, *(undefined *)(in_lr + -0x28));
    method.Presonus::Panel::OutputPin.set_int(c, arg1, *(undefined *)(in_lr + -0x24));
    sub.fclose_c5f88(arg1, *(undefined *)(in_lr + -0x20));
    return;
}
```	

## Panel Reset - not confirmed

* 0x66 (offs: `102`) - Reset? 0 == reset, 1 == normal mode

The following code resets FP to normal or boot mode. If you don't configure boot pin, you will get into `BOOT` mode
```bash
PIN=$(($GPIO_BASE+102))
echo $PIN > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio$PIN/direction
echo 0 > /sys/class/gpio/gpio$PIN/value
sleep 1
echo 1 > /sys/class/gpio/gpio$PIN/value
sleep 1

```

## Panel Hearbeat( as input! ) and boot mode (Output)

* 0x6e (offs: `110`) - Boot/Heartbeat, 1 == boot, 0 == normal

Calling will output toggling 1/0

```bash
PIN=$(($GPIO_BASE+110))
echo $PIN > /sys/class/gpio/export
echo in > /sys/class/gpio/gpio$PIN/direction
while true; do cat /sys/class/gpio/gpio$PIN/value; done

```

Set boot
```bash
PIN=$(($GPIO_BASE+110))
echo $PIN > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio$PIN/direction
echo 0 > /sys/class/gpio/gpio$PIN/value

```

Set Normal
```bash
PIN=$(($GPIO_BASE+110))
echo $PIN > /sys/class/gpio/export
echo in > /sys/class/gpio/gpio$PIN/direction

```

Deduced from

```cpp
void method.Presonus::Surface::PanelRegistrar.resetPanel_int(int32_t arg2)
{
    int32_t pin_0x6e_boot; // boot
    int32_t pin_0x66_reset; // reset
    int32_t iStack44;
    int32_t iStack40;
    
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&pin_0x66_reset); // make output
    method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&pin_0x66_reset); // set 0
    method.Core::Threads.sleep_unsigned_int(10);
    if (arg2 == 0) {  // enter boot mode?
        sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&pin_0x6e_boot); // make output
        method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&pin_0x6e_boot);  // set 0
        method.Core::Threads.sleep_unsigned_int(10);
        method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&pin_0x66_reset); // set 1
        method.Core.DebugPrintf_char_const___...(iStack40, iStack44); //"Panel: set to bootloader Mode\n"
        sub.fclose_c5f88((int32_t)&pin_0x6e_boot);
    } else {
        method.Presonus::Panel::InputPin.InputPin_int__Presonus::Panel::PinStateObserver(0x6e, (int32_t)&pin_0x6e_boot); //make boot input, //Watch heartbeat?
        method.Core::Threads.sleep_unsigned_int(10);
        method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&pin_0x66_reset); // set 1
        method.Core::Threads.sleep_unsigned_int(10);
        method.Core.DebugPrintf_char_const___...(iStack40, iStack44); //"Panel: set to normal mode\n"
        method.Presonus::Panel::InputPin._InputPin((int32_t)&pin_0x6e_boot); // make input
    }
    sub.fclose_c5f88((int32_t)&pin_0x66_reset);
    return;
}
```

## Audio Reset

```cpp
void method.Presonus::Surface::PanelRegistrar.resetAudio_bool(int32_t arg1, int32_t arg2)
{
    int32_t arg1_00;
    int32_t arg1_01;
    int32_t *piVar1;
    int32_t var_54h;
    int32_t var_44h;
    undefined auStack68 [12];
    int32_t var_34h;
    undefined auStack52 [12];
    undefined4 uStack4;
    
    uStack4 = 0xa4b04;
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_34h);
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_44h);
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_54h);
    if (arg2 == 0) {
        arg1_00 = method.Presonus::DelayTimer.isLongEnoughYet___const(arg1 + 0x110);
        piVar1 = &var_44h;
        if (arg1_00 != 0) {
            arg1_00 = method.Presonus::Panel::ControlRegistrar.findGroup_int__const(arg1);
            arg1_01 = method.Presonus::Panel::ControlGroup.byTag_int__const(arg1_00);
            arg1_01 = method.Presonus::Panel::Control.getParameter___const(arg1_01);
            arg1_00 = method.Presonus::Panel::ControlGroup.byTag_int__const(arg1_00);
            arg1_00 = method.Presonus::Panel::Control.getParameter___const(arg1_00);
            piVar1 = (int32_t *)auStack52;
            if (arg1_01 != 0 && arg1_00 != 0) {
                method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_34h);
                method.Core::Portable::Parameter.changed(arg1_01);
                method.Core::Portable::Parameter.changed(arg1_00);
                method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_44h);
                method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_54h);
                method.Presonus::DelayTimer.reset(arg1 + 0x110);
                piVar1 = (int32_t *)&stack0xffffffe4;
            }
        }
    } else {
        method.Presonus::DelayTimer.beginAction_float(arg1 + 0x110);
        method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_34h);
        method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_44h);
        piVar1 = (int32_t *)(auStack68 + 4);
    }
    sub.fclose_c5f88(&var_54h, *(undefined *)piVar1);
    sub.fclose_c5f88(&var_44h, *(undefined *)((int32_t)piVar1 + 4));
    sub.fclose_c5f88(&var_34h, *(undefined *)((int32_t)piVar1 + 8));
    return;
}
```

## Scribble Strips

There seems to be Common scribble strip display reset pin, yet its number is unknown

```cpp
void method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
               (int32_t fd, int32_t arg_4h)
{
    int32_t in_r3;
    int32_t *piVar1;
    int32_t var_6ch;
    int32_t var_68h;
    int32_t var_64h;
    int32_t var_60h;
    int32_t var_5ch;
    int32_t var_58h;
    int32_t var_54h;
    int32_t var_50h;
    int32_t var_4ch;
    int32_t var_48h;
    int32_t var_40h;
    undefined var_2eh [2];
    int32_t var_2ch;
    
    var_2eh[0] = 0x30;
    var_54h = 1;
    var_58h = 0;
    var_64h = (int32_t)var_2eh;
    sym.imp.ioctl(fd, *(undefined4 *)0xb2880, &var_64h);
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_40h);
    method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_40h);
    var_58h = 0;
    var_54h = 1;
    var_64h = (int32_t)var_2eh;
    sym.imp.ioctl(fd, *(undefined4 *)0xb2880, &var_64h);
    method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_40h);
    piVar1 = &var_58h;
    if (0 < arg_4h) {
        var_58h = 0;
        var_54h = arg_4h;
        var_64h = in_r3;
        sym.imp.ioctl(fd, *(undefined4 *)0xb2880, &var_64h);
        piVar1 = &var_54h;
    }
    sub.fclose_c5f88(&var_40h, *(undefined *)piVar1);
    return;
}

```


```cpp

int32_t sym.Presonus::Surface::LCDPort::LCDPort(int32_t arg1)
{
    *(undefined4 *)arg1 = *(undefined4 *)0xb26d0;
    sym.Core::IO::Buffer::Buffer_void___unsigned_int__bool(0);
    sym.Presonus::ScribbleStripMgr::ScribbleStripMgr(arg1 + 0x14);
    return arg1;
}

int32_t sym.Presonus::ScribbleStripMgr::ScribbleStripMgr(int32_t arg1)
{
    method.Presonus::ScribbleStripMgr.initDisplayModules(arg1);
    return arg1;
}

void method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
               (int32_t fd, int32_t arg_4h)
{
    int32_t in_r3;
    int32_t *piVar1;
    int32_t var_6ch;
    int32_t var_68h;
    int32_t var_64h;
    int32_t var_60h;
    int32_t var_5ch;
    int32_t var_58h;
    int32_t var_54h;
    int32_t var_50h;
    int32_t var_4ch;
    int32_t var_48h;
    int32_t var_40h;
    undefined var_2eh [2];
    int32_t var_2ch;
    
    var_2eh[0] = 0x30;
    var_54h = 1;
    var_58h = 0;
    var_64h = (int32_t)var_2eh;
    sym.imp.ioctl(fd, *(undefined4 *)0xb2880, &var_64h);
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_40h);
    method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_40h);
    var_58h = 0;
    var_54h = 1;
    var_64h = (int32_t)var_2eh;
    sym.imp.ioctl(fd, *(undefined4 *)0xb2880, &var_64h);
    method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_40h);
    piVar1 = &var_58h;
    if (0 < arg_4h) {
        var_58h = 0;
        var_54h = arg_4h;
        var_64h = in_r3;
        sym.imp.ioctl(fd, *(undefined4 *)0xb2880, &var_64h);
        piVar1 = &var_54h;
    }
    sub.fclose_c5f88(&var_40h, *(undefined *)piVar1);
    return;
}


undefined4
method.Presonus::ScribbleStripMgr.writeToScribbleStrip_int__Core::BitmapData_const(int32_t arg2, int32_t arg1)
{
    uint8_t *puVar1;
    undefined4 uVar2;
    undefined4 *puVar3;
    int32_t in_r2;
    uint32_t uVar4;
    uint32_t uVar5;
    uint32_t uVar6;
    undefined *puVar7;
    int32_t fd;
    uint32_t uVar8;
    bool bVar9;
    int32_t in_stack_ffffffb8;
    int32_t in_stack_ffffffbc;
    undefined auStack60 [2];
    int32_t var_36h;
    
    if (arg2 < 0) {
        method.Core.DebugPrintf_char_const___...(in_stack_ffffffbc, in_stack_ffffffb8); // "ScribbleStripMgr::writeToScribbleStrip display number %d out of range\n"
        uVar2 = 1;
    } else {
        fd = 0;
        do {
            uVar6 = 0;
            puVar7 = (undefined *)(arg1 + fd * 8);
            do {
                uVar8 = 0;
                puVar1 = (uint8_t *)
                         (*(int32_t *)(in_r2 + 0xc) + *(int32_t *)(in_r2 + 0x10) * fd + ((int32_t)uVar6 >> 3));
                uVar4 = 0;
                do {
                    uVar5 = (uint32_t)*puVar1;
                    puVar1 = puVar1 + *(int32_t *)(in_r2 + 0x10);
                    bVar9 = (0x80 >> (uVar6 & 7) & uVar5) != 0;
                    if (bVar9) {
                        uVar5 = uVar8 | 0x80 >> (uVar4 & 0xff);
                    }
                    uVar4 = uVar4 + 1;
                    if (bVar9) {
                        uVar8 = uVar5 & 0xff;
                    }
                } while (uVar4 != 8);
                uVar6 = uVar6 + 1;
                *puVar7 = (char)uVar8;
                puVar7 = puVar7 + 1;
            } while (uVar6 != 0x40);
            fd = fd + 8;
        } while (fd != 0x60);
        fd = sym.imp.open(*(undefined4 *)(*(int32_t *)0xb2a00 + (arg2 >> 2 & 3U) * 4), 1);
        if (fd == -1) {
            puVar3 = (undefined4 *)sym.imp.__errno_location();
            sym.imp.strerror(*puVar3);
            method.Core.DebugPrintf_char_const___...(stack0xffffffc8, _auStack60); // "writeToScribbleStrip failed to open device %s [%s]\n"
            uVar2 = 0;
        } else {
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int(fd, 2);
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int(fd, 2);
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int(fd, 0x300);
            sym.imp.close(fd);
            uVar2 = 1;
        }
    }
    return uVar2;
}

void method.Presonus::ScribbleStripMgr.initDisplayModules(int32_t arg1)
{

	/*

	fp = 0xb26d0 + 14

	mov ip, sp
0x000b2a10      push {r4, r5, r6, r7, r8, sb, sl, fp, ip, lr, pc}
0x000b2a14      sub sp, sp, 0xc20
0x000b2a18      sub fp, ip, 4
0x000b2a1c      sub sp, sp, 0xc
0x000b2a20      mov r1, 0x1d
0x000b2a24      mov r6, r0         ; arg1
0x000b2a28      sub r0, fp, 0x48

	; var void *s @ fp-0xc30
; var int32_t var_48h @ fp-0x48
; var int32_t var_36h @ fp-0x36
; var int32_t var_35h @ fp-0x35
; var int32_t var_34h @ fp-0x34
; var int32_t var_33h @ fp-0x33
; var int32_t var_32h @ fp-0x32
; var int32_t var_31h @ fp-0x31
; var int32_t var_30h @ fp-0x30
; var int32_t var_2fh @ fp-0x2f
; var int32_t var_c2ch @ sp+0x0
; arg int32_t arg1 @ r0

*/
    int32_t fd;
    undefined4 *puVar1;
    int32_t iVar2;
    undefined *puVar3;
    undefined auStack3148 [8];
    undefined auStack3140 [16];
    void *s;
    int32_t var_48h;
    int32_t var_36h;
    
    //looks like modules reset
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_48h);
    method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_48h);
    method.Core::Threads.sleep_unsigned_int(100);
    method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_48h);
    method.Core::Threads.sleep_unsigned_int(500);
    puVar3 = auStack3140;
    iVar2 = 0;


/* loop through
/dev/spidev1.0
/dev/spidev1.1
/dev/spidev1.6
/dev/spidev1.7
*/

    do {
        fd = sym.imp.open(*(undefined4 *)(*(int32_t *)0xb2f2c + iVar2), 1);
        if (fd == -1) {
            puVar1 = (undefined4 *)sym.imp.__errno_location();
            sym.imp.strerror(*puVar1);
            method.Core.DebugPrintf_char_const___...(*(int32_t *)(puVar3 + 0x10), *(int32_t *)(puVar3 + 0xc)); // "initDisplayModules failed to open device %s [%s]\n"
            puVar3 = puVar3 + 0x10;
        } else {
            *(undefined4 *)(puVar3 + 4) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 4));
            *(undefined4 *)(puVar3 + 8) = 1;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 8));
            *(undefined4 *)(puVar3 + 0xc) = 1;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0xc));
            method.Core::Threads.sleep_unsigned_int(10, puVar3[0x10]);
            *(undefined4 *)(puVar3 + 0x14) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x14));
            method.Core::Threads.sleep_unsigned_int(0x14, puVar3[0x18]);
            *(undefined4 *)(puVar3 + 0x1c) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x1c));
            *(undefined4 *)(puVar3 + 0x20) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x20));
            *(undefined4 *)(puVar3 + 0x24) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x24));
            method.Core::Threads.sleep_unsigned_int(0x14, puVar3[0x28]);
            *(undefined4 *)(puVar3 + 0x2c) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x2c));
            *(undefined4 *)(puVar3 + 0x30) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x30));
            *(undefined4 *)(puVar3 + 0x34) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x34));
            *(undefined4 *)(puVar3 + 0x38) = 1;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x38));
            method.Core::Threads.sleep_unsigned_int(0x32, puVar3[0x3c]);
            *(undefined4 *)(puVar3 + 0x40) = 1;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x40));
            *(undefined4 *)(puVar3 + 0x44) = 2;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x44));
            *(undefined4 *)(puVar3 + 0x48) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x48));
            *(undefined4 *)(puVar3 + 0x4c) = 3;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x4c));
            *(undefined4 *)(puVar3 + 0x50) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x50));
            *(undefined4 *)(puVar3 + 0x54) = 1;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x54));
            *(undefined4 *)(puVar3 + 0x58) = 3;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x58));
            *(undefined4 *)(puVar3 + 0x5c) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x5c));
            *(undefined4 *)(puVar3 + 0x60) = 1;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x60));
            *(undefined4 *)(puVar3 + 100) = 1;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 100));
            *(undefined4 *)(puVar3 + 0x68) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x68));
            *(undefined4 *)(puVar3 + 0x6c) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x6c));
            *(undefined4 *)(puVar3 + 0x70) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x70));
            *(undefined4 *)(puVar3 + 0x74) = 4;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x74));
            *(undefined4 *)(puVar3 + 0x78) = 3;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x78));
            *(undefined4 *)(puVar3 + 0x7c) = 8;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x7c));
            *(undefined4 *)(puVar3 + 0x80) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x80));
            sym.imp.memset(auStack3148, 0, 0xc00);
            *(undefined4 *)(puVar3 + 0x88) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x88));
            *(undefined4 *)(puVar3 + 0x8c) = 2;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x8c));
            *(undefined4 *)(puVar3 + 0x90) = 2;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x90));
            *(undefined4 *)(puVar3 + 0x94) = 0xc00;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x94));
            *(undefined4 *)(puVar3 + 0x98) = 0;
            method.Presonus::ScribbleStripMgr.txCommandDataArray_int__unsigned_char__unsigned_char___int
                      (fd, *(int32_t *)(puVar3 + 0x98));
            sym.imp.close(fd);
            puVar3 = puVar3 + 0xa0;
        }
        iVar2 = iVar2 + 4;
    } while (iVar2 != 0x10);
    sub.fclose_c5f88(&var_48h, *puVar3);
    return;
}
```

## Dice III programmer

```cpp
void method.Presonus::DICE::Dice3Subsystem.resetDice3(void)
{
    int32_t var_24h;
    
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_24h);
    method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_24h);
    method.Core::Threads.sleep_unsigned_int(1);
    method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_24h);
    sub.fclose_c5f88((int32_t)&var_24h);
    return;
}
```

```cpp
undefined4 method.Presonus::DICE::Dice3Programmer.open_char_const(int32_t arg1, char *path)
{
    int32_t iVar1;
    undefined4 uVar2;
    int32_t *piVar3;
    int32_t var_40h;
    int32_t var_30h;
    int32_t var_20h;
    int32_t var_1ch;
    undefined4 uStack4;
    
    uStack4 = 0xcea40;
    piVar3 = &var_1ch;
    iVar1 = sym.imp.open(path, 2);
    *(int32_t *)arg1 = iVar1;
    if (-1 < iVar1) {
        var_20h = 0;
        iVar1 = sym.imp.ioctl(iVar1, *(undefined4 *)0xceb6c, &var_20h);
        if (-1 < iVar1) {
            var_20h = var_20h & 0xfffffffc;
            iVar1 = sym.imp.ioctl(*(undefined4 *)arg1, *(undefined4 *)0xceb70, &var_20h);
            if (-1 < iVar1) {
                sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_30h);
                method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_30h);
                method.Core::Threads.sleep_unsigned_int(1);
                sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_40h);
                method.Presonus::Panel::OutputPin.set_int(0, (int32_t)&var_40h);
                method.Core::Threads.sleep_unsigned_int(1);
                iVar1 = method.Presonus::DICE::Dice3Programmer.readJedecId(arg1);
                if (iVar1 == *(int32_t *)0xceb74) {
                    uVar2 = 1;
                } else {
                    if (*(int32_t *)arg1 != -1) {
                        sym.imp.close();
                        piVar3 = (int32_t *)&stack0xffffffe4;
                        *(undefined4 *)arg1 = 0xffffffff;
                    }
                    uVar2 = 0;
                }
                sub.fclose_c5f88(&var_40h, *(undefined *)piVar3);
                sub.fclose_c5f88(&var_30h, *(undefined *)(piVar3 + 1));
                return uVar2;
            }
        }
    }
    return 0;
}
```

```cpp
void method.Presonus::DICE::Dice3Programmer.close(int32_t arg1)
{
    undefined *puVar1;
    int32_t var_3ch;
    int32_t var_2ch;
    undefined auStack40 [4];
    undefined auStack36 [8];
    undefined4 uStack4;
    
    uStack4 = 0xce998;
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_2ch);
    method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_2ch);
    method.Core::Threads.sleep_unsigned_int(1);
    sym.Presonus::Panel::OutputPin::OutputPin_int((int32_t)&var_3ch);
    method.Presonus::Panel::OutputPin.set_int(1, (int32_t)&var_3ch);
    method.Core::Threads.sleep_unsigned_int(1);
    puVar1 = auStack40;
    if (*(int32_t *)arg1 != -1) {
        sym.imp.close();
        puVar1 = auStack36;
    }
    sub.fclose_c5f88(&var_3ch, *puVar1);
    sub.fclose_c5f88(&var_2ch, puVar1[4]);
    return;
}
```