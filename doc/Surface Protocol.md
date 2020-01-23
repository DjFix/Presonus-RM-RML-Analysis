# Surface protocol

## Serial setup

Communication is done via ttyS1. To setup port for manipulations from terminal use

```
stty -F /dev/ttyS1 speed 115200 cs8 -cstopb -parenb -isig -icanon -iexten -echo -brkint -icrnl -imaxbel -opost
```

Port configuration before `surface` start

```
stty -F /dev/ttyS1
speed 115200 baud;
intr = ^C; quit = ^\; erase = ^?; kill = ^U; eof = ^D; eol = <undef>;
eol2 = <undef>; start = ^Q; stop = ^S; susp = ^Z; rprnt = ^R; werase = ^W;
lnext = ^V; flush = ^O; min = 1; time = 0;
-brkint -imaxbel
```

Port configuration after `surface` start

```
/ # stty -F /dev/ttyS1
speed 115200 baud;
intr = ^C; quit = ^\; erase = ^?; kill = ^U; eof = ^D; eol = <undef>;
eol2 = <undef>; start = ^Q; stop = ^S; susp = ^Z; rprnt = ^R; werase = ^W;
lnext = ^V; flush = ^O; min = 0; time = 0;
-brkint -icrnl -imaxbel
-opost
-isig -icanon -iexten -echo
```

Reading commands from surface can be done with
```
cat /dev/ttyS1 &
```

## Firmware upgrade mode

* `A000g` - First bar
* `A009g` - 10% fill
* `A019g` - 25% fill
* `A028g` - 40% fill
* `A009g` - 10% fill
* `A032g` - 50% fill
* `A066g` - 100% fill

***NB1** Progress bar seems to be timed and fills itself slowly*
***NB2** You can exit from progress by issuing `B001g`*
***NB3** You cannot reset progress to a lower value*

## Boot status indication

* `B000g` - Start bouncing LED meters pattern, sent by u-boot stage
* `B001g` - Stop bouncing LED meters pattern, sent by Kernel stage in `S05pslash` script

## LEDs

Leds are RGB and single color. 

RGB leds are:
* All select buttons, except `cntr/mono` and `Left/Right`
* All Faders section buttons, except `Mix Masters`
* `Groups` button
* `Marker` button

## Button events

Button event is coded in format 
	* `<key code>s` for key press
	* `<key code>S` for key release

### Key Codes

#### Input section
* `707` - +48V
* `708` - Phase

#### Gate section
* `700` - ON
* `701` - Edit

#### Compressor section
* `702` - ON
* `703` - Edit

#### Limiter section
* `704` - ON

#### EQ Section
* `705` - ON
* `706` - Edit

#### Stereo section
* `70C` - Link

#### Assign section
* `70B` - LR
* `70A` - Mono
* `709` - Edit

#### Channel section
* `70F` - Copy 
* `70E` - Edit
* `70D` - Save
* `711` - ALT

#### Talkback section
* `A02` - Talk
* `A03` - Main 
* `A04` - All
* `A05` - Custom
* `A06` - Edit

#### Solo section
* `A00` - Clear
* `A01` - Edit

#### Geq section
* `710` - GEQ

#### Mute Groups
* `800` - 1
* `801` - 2
* `802` - 3
* `803` - 4
* `804` - 5
* `805` - 6
* `806` - 7
* `807` - 8
* `808` - All On
* `809` - All Off

#### Monitor section
* `A07` - Solo
* `A08` - Mono
* `A09` - Cue
* `A0A` - Edit

#### Master control
* `A0B` - Home
* `A0C` - Store
* `A0D` - Recall
* `A0E` - UCNET
* `A25` - Group
* `A26` - TAP
* `A23` - Marker
* `A0F` - Scenes
* `A10` - Quick Recall

#### Mix section
* `600` - 1
* `601` - 2
* `602` - 3
* `603` - 4
* `604` - 5
* `605` - 6
* `606` - 7
* `607` - 8
* `608` - 9
* `609` - 10
* `60A` - 11
* `60B` - 12
* `60C` - 13
* `60D` - 14
* `60E` - 15
* `60F` - 16
* `610` - FX1
* `611` - FX2
* `612` - FX3
* `613` - FX4
* `614` - Main

#### Transport section
* `A13` - Back
* `A11` - Stop
* `A24` - Play
* `A13` - Rec

#### Select section
* `000` - 1
* `001` - 2
* `002` - 3
* `003` - 4
* `004` - 5
* `005` - 6
* `006` - 7
* `007` - 8
* `008` - 9
* `009` - 10
* `00A` - 11
* `00B` - 12
* `00C` - 13
* `00D` - 14
* `00E` - 15
* `00F` - 16
* `010` - Cntr/Mono
* `011` - Left/Right
* `012` - Flex

#### Solo section
* `100` - 1
* `101` - 2
* `102` - 3
* `103` - 4
* `104` - 5
* `105` - 6
* `106` - 7
* `107` - 8
* `108` - 9
* `109` - 10
* `10A` - 11
* `10B` - 12
* `10C` - 13
* `10D` - 14
* `10E` - 15
* `10F` - 16
* `110` - Flex

#### Mute section
* `200` - 1
* `201` - 2
* `202` - 3
* `203` - 4
* `204` - 5
* `205` - 6
* `206` - 7
* `207` - 8
* `208` - 9
* `209` - 10
* `20A` - 11
* `20B` - 12
* `20C` - 13
* `20D` - 14
* `20E` - 15
* `20F` - 16
* `210` - FX1
* `211` - FX2
* `212` - FX3
* `213` - FX4
* `214` - Flex

#### Fader Layers
* `A1D` - A
* `A1E` - B
* `A1F` - C
* `A20` - D
* `A17` - Returns
* `A18` - Mix Masters
* `A21` - Group Masters
* `A22` - DAW

#### Led meter layers

* `A19` - Inpup
* `A1A` - Output
* `A1B` - GR
* `A1C` - Mixes

