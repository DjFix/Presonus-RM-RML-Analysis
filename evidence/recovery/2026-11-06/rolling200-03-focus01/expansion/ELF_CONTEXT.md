# ELF context

Full target ranges verified against exact source ELF. Static evidence; C++ return/layout remains unresolved.
One-hop calls/references only. Neighbor bodies require explicit expansion. Pseudocode is unvalidated.

## __aeabi_f2iz

ELF `304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0`; version `CS18AI surface 13840`; `client`; original `__aeabi_f2iz`; address `0x1877f8`; size 92; section .text; SHA256 `73908d204e4625c30fc21dff9a2f817e26c53d161164a032bd229a9dcdd6edee`
Original ELF path: `rootfs/CS18_v13840/home/root/surface`; file offset `0x17f7f8`. Exact full range is offset + size; includes any literal pool bytes.

```asm
001877f8  8020a0e1  lsl r2, r0, #1
001877fc  7f0452e3  cmp r2, #0x7f000000
00187800  0800003a  blo #0x187828
00187804  9e30a0e3  mov r3, #0x9e
00187808  222c53e0  subs r2, r3, r2, lsr #24
0018780c  0700009a  bls #0x187830
00187810  0034a0e1  lsl r3, r0, #8
00187814  023183e3  orr r3, r3, #0x80000000
00187818  020110e3  tst r0, #0x80000000
0018781c  3302a0e1  lsr r0, r3, r2
00187820  00006012  rsbne r0, r0, #0
00187824  1eff2fe1  bx lr
00187828  0000a0e3  mov r0, #0
0018782c  1eff2fe1  bx lr
00187830  610072e3  cmn r2, #0x61
00187834  0100001a  bne #0x187840
00187838  8024b0e1  lsls r2, r0, #9
0018783c  0200001a  bne #0x18784c
00187840  020110e2  ands r0, r0, #0x80000000
00187844  0201e003  mvneq r0, #0x80000000
00187848  1eff2fe1  bx lr
0018784c  0000a0e3  mov r0, #0
00187850  1eff2fe1  bx lr
```

### Unvalidated pseudocode — declarations are not evidence

```text
// UNVALIDATED DECOMPILER OUTPUT. Not buildable C++ or an ABI declaration.
// __fixsfsi
// Symbol __fixsfsi address=0x1877f8
unsigned int __aeabi_f2iz(unsigned int a0)
{
    unsigned int v0;  // r2
    unsigned int v1;  // r2

    v0 = a0 * 2;
    if (v0 < 0x7f000000)
        return 0;
    v1 = 158 - (v0 >> 24);
    if (158 <= v0 >> 24)
    {
        if (v1 == 0xffffff9f && a0 * 0x200)
            return 0;
        if (a0 & 0x80000000)
            return a0 & 0x80000000;
        return 0x7fffffff;
    }
    else if (a0 & 0x80000000)
    {
        return -((a0 * 0x100 | 0x80000000) >> ((char)v1 & 31) & (int)((v1 & 0xff) - 32) >> 31);
    }
    else
    {
        return (a0 * 0x100 | 0x80000000) >> ((char)v1 & 31) & (int)((v1 & 0xff) - 32) >> 31;
    }
}


```

## Typed relationships

- ELF_CALLS: `LPFControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x90b24; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::PanControl::drawValueMark(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x67fa8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::PanControl::drawImagePanner(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x68d1c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::PanControl::drawImagePanner(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x68e98; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::PanControl::drawImagePanner(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x68f80; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::PanControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x69124; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::PanControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x691f0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::PotControl::changeFrames()` → `__aeabi_f2iz` at 0x65a98; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::GridPainter::paintGrid(Core::TRect<int> const&, Core::TRect<int> const&, Core::Portable::DrawEvent const&, Core::Portable::Style const&)` → `__aeabi_f2iz` at 0x6d63c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::GridPainter::paintGrid(Core::TRect<int> const&, Core::TRect<int> const&, Core::Portable::DrawEvent const&, Core::Portable::Style const&)` → `__aeabi_f2iz` at 0x6d658; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::WIFIManager::ConfigNetworkTask::config()` → `__aeabi_f2iz` at 0xc9838; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::SLChannelBase::updateColorFromIndex()` → `__aeabi_f2iz` at 0x5e4f4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::McuVpotControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x66af8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::McuVpotControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x66b14; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::McuVpotControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x66c38; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x725d0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x725dc; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x725f8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x72604; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x72628; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x7267c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x7268c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::calculatePivotPoints(int&, int&, int&, int&)` → `__aeabi_f2iz` at 0x7269c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DynamicsControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x73414; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::SpectrumPainter::calculateBars(Core::TRect<int> const&)` → `__aeabi_f2iz` at 0x6b380; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::FocusHelperButton::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x64a14; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::MeterScaleControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x66ee8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::MeterScaleControl::draw(Core::Portable::DrawEvent const&)` → `__aeabi_f2iz` at 0x66fb4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DAWClientComponent::channelParamChanged(Presonus::DAWChannel*, Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x53e24; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::UC::FileTransferManager::processIdle()` → `__aeabi_f2iz` at 0x257cc; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::LEDControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x189c4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::PanMeterControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18360; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::DigitalPotControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18c04; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::LCDDisplayControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18200; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18504; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18540; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x1876c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x187ac; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x1880c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18850; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18924; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MeterLevelControl::transmit()` → `__aeabi_f2iz` at 0x17c40; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::PhantomPowerControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18bac; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MotorizedFaderControl::handleTouch(bool)` → `__aeabi_f2iz` at 0x15fd8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Panel::MotorizedFaderControl::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x18c60; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::PanelRegistrar::getFaderSpeed()` → `__aeabi_f2iz` at 0xa5f50; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::PanelRegistrar::bumpFaderSpeed(int)` → `__aeabi_f2iz` at 0xa5ea8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::PanelRegistrar::getFaderSensitivity()` → `__aeabi_f2iz` at 0xa5e68; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::PanelRegistrar::bumpFaderTouchSensitivity(int)` → `__aeabi_f2iz` at 0xa5dbc; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::PanelRegistrar::onIdle()` → `__aeabi_f2iz` at 0xa5c50; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::PanelRegistrar::onIdle()` → `__aeabi_f2iz` at 0xa5cd0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SLMixerHandler::assignFxTargets()` → `__aeabi_f2iz` at 0x8b29c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::MappingComponent::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x80bbc; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::MappingComponent::handleFootswitch(bool)` → `__aeabi_f2iz` at 0x7f0a8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::AvbSetupCompanion::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x9f9fc; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::WifiSetupComponent::updateDisplayList()` → `__aeabi_f2iz` at 0x9fb38; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::doTestMode(Presonus::Surface::SurfaceTestMode)` → `__aeabi_f2iz` at 0xadf44; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::doTestMode(Presonus::Surface::SurfaceTestMode)` → `__aeabi_f2iz` at 0xadf8c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::doTestMode(Presonus::Surface::SurfaceTestMode)` → `__aeabi_f2iz` at 0xadfd4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::doTestMode(Presonus::Surface::SurfaceTestMode)` → `__aeabi_f2iz` at 0xae018; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::stopAllTests()` → `__aeabi_f2iz` at 0xad64c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::stopAllTests()` → `__aeabi_f2iz` at 0xad680; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitUtilPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xad6f4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitUtilPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xad71c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedLcdBrightness(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xad27c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedCalibrationTarget(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xad48c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitDiagnositcsPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xad99c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitDiagnositcsPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xad9c4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitDiagnositcsPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xada14; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitDiagnositcsPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xada54; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitDiagnositcsPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xadaa4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitAudioUtilitiesPage()` → `__aeabi_f2iz` at 0xadb80; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitAudioUtilitiesPage()` → `__aeabi_f2iz` at 0xadbc0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitAudioUtilitiesPage()` → `__aeabi_f2iz` at 0xadc00; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitAudioUtilitiesPage()` → `__aeabi_f2iz` at 0xadc40; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitCalibrateTouchPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xadc8c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitFaderUtilitiesPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xadb18; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SurfaceRootComponent::paramChangedExitTestTouchscreenPage(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0xad900; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::NetworkSetupComponent::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0xa373c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::NetworkSetupComponent::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0xa388c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::NetworkSetupComponent::NetworkSetupComponent(char const*, int)` → `__aeabi_f2iz` at 0xa1ad0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::NetworkSetupComponent::NetworkSetupComponent(char const*, int)` → `__aeabi_f2iz` at 0xa1f78; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::FxPresetsPageComponent::onShow(bool)` → `__aeabi_f2iz` at 0xb5dfc; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::TBRoutingPageComponent::paramChanged(Core::Portable::Parameter*, int)` → `__aeabi_f2iz` at 0x99844; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::TBRoutingPageComponent::updateLocalTalkbackSource(Core::Portable::Parameter*)` → `__aeabi_f2iz` at 0x9617c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::GeqPresetsPageComponent::getTargetUrl(Core::CStringBuffer<256>&)` → `__aeabi_f2iz` at 0xb4180; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::MeterControl::normalizedToPixel(float) const` → `__aeabi_f2iz` at 0x650ac; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::MeterControl::normalizedToPixel(float) const` → `__aeabi_f2iz` at 0x650cc; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::SLChannelBase::getColorIndex() const` → `__aeabi_f2iz` at 0x5daf0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DAWChannelGroup::getUsedCount() const` → `__aeabi_f2iz` at 0x52f0c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::DAWDeviceFolder::getUsedCount() const` → `__aeabi_f2iz` at 0x52e54; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::UC::Format::ChannelNameFormatter::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0x4caa0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Dsp::PanFormatter::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0xc3fa8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Dsp::GainDBFormatter::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0xc3da0; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Dsp::CounterFormatter::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0xc3068; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Dsp::MillisecondsFormatter::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0xc3a8c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Mixer::NumberPrepender::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0xf5c4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Mixer::GeqFreqFormatter::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0xf444; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Mixer::SubDelayFormatter::print(Core::Formatter::Data&) const` → `__aeabi_f2iz` at 0xef8c; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::SLMixerHandler::getSelectedGeq() const` → `__aeabi_f2iz` at 0x81578; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::EQPageComponent::getEqEncoderMode() const` → `__aeabi_f2iz` at 0x8dc74; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::DawFxPageComponent::isSendMode() const` → `__aeabi_f2iz` at 0xb72e8; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::WifiSetupComponent::getMaxListOffset() const` → `__aeabi_f2iz` at 0x9f210; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::NetworkSetupComponent::getTargetType() const` → `__aeabi_f2iz` at 0x9f504; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::Surface::NetworkSetupComponent::getWiredNetworkAssignMode() const` → `__aeabi_f2iz` at 0x9f278; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::EQControl::freqToX(float) const` → `__aeabi_f2iz` at 0x6bd48; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::EQControl::gainToY(float) const` → `__aeabi_f2iz` at 0x6c1b4; {"instruction": "bl", "target_address": 1603576}
- ELF_CALLS: `Presonus::EQControl::getType(int) const` → `__aeabi_f2iz` at 0x6ab78; {"instruction": "bl", "target_address": 1603576}

## External-source bindings — do not reconstruct these providers from firmware


## Bound raw data

{}
