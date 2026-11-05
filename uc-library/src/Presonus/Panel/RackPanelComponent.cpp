#include "presonus/panel/RackPanelComponent.hpp"
#include "core/system/coredebug.h"
#include "core/system/coretime.h"
#include "presonus/mixer/MixerComponentBase.hpp"
namespace Presonus::Panel {
namespace {
using Core::Portable::ParamInfo;
const char *offOn[] = {"Off", "On"};
// Intentional host ParamInfo adaptation of exact five native 84-byte records.
const ParamInfo rackParameters[] = {
    {2, 1, "meters_48v", 0.f, 1.f, 0.f, 0.f, 1.f, 0, nullptr, nullptr, offOn,
     "Meters-48V toggle", nullptr},
    {2, 2, "powerled_red", 0.f, 1.f, 0.f, 0.f, 1.f, 0, nullptr, nullptr, offOn,
     "Power LED red", nullptr},
    {2, 3, "powerled_blue", 0.f, 1.f, 0.f, 0.f, 1.f, 0, nullptr, nullptr, offOn,
     "Power LED blue", nullptr},
    {2, 4, "phones_cue", 0.f, 1.f, 0.f, 0.f, 1.f, 0, nullptr, nullptr, offOn,
     "Phones monitor Cue", nullptr},
    {2, 5, "phones_main", 0.f, 1.f, 0.f, 0.f, 1.f, 0, nullptr, nullptr, offOn,
     "Phones monitor Cue", nullptr},
};
} // namespace
RackPanelComponent::RackPanelComponent(Presonus::Mixer::MixerComponentBase &m,
                                       PanelRegistrar &r)
    : PanelComponent(static_cast<presonus::panel_port::PanelCore &>(*this), m,
                     r),
      meterLEDs(meterControls), clipLEDs(clipControls),
      phantomLEDs(phantomControls) {
  mixer = &m;
  // Keep each real CCL parameter owned until ParamList accepts it. The
  // upstream bulk add allocates the parameter before its vector can grow;
  // this source-port guard also unwinds that allocation if growth throws.
  for (const auto &info : rackParameters) {
    auto parameter = std::make_unique<Core::Portable::ListParam>(info);
    paramList.add(parameter.get());
    parameter.release();
  }
}
RackPanelComponent::~RackPanelComponent() = default;

void RackPanelComponent::clientsChanged() { updatePanelStatus(); }
void RackPanelComponent::checkPermissionsPWReset() {
  if (permissionFlags & 0x18u)
    return;
  // Intentional source adaptation: CCL milliseconds replace original signed
  // nanoseconds divided by 1000000. The comparison retains ARM subtraction's
  // wrapping bit pattern and signed high-word decision without signed overflow.
  const auto milliseconds = Core::SystemClock::getMilliseconds();
  const auto elapsed =
      static_cast<std::uint64_t>(milliseconds) - *permissionStartupMilliseconds;
  if ((elapsed >> 63) != 0 || elapsed < 1000)
    return;
  permissionFlags |= 0x10u;
  if ((permissionFlags & 5u) == 5u)
    mixer->resetPermissionsPW();
}
void RackPanelComponent::forceCascadeGlobalParamUpdate() {
  auto &parameters = *mixer->cascadeParameters;
  for (int tag : {7, 8, 9, 10, 11, 12, 13, 15, 14, 19, 28, 20})
    parameters.getParameterByTag(tag)->changed();
}
void RackPanelComponent::help() {
  Core::DebugPrintf("\n******************************\n");
  Core::DebugPrintf("tests available:\n");
  Core::DebugPrintf("    ./mixer erase\n");
  Core::DebugPrintf("    ./mixer dsp <script path>\n");
  Core::DebugPrintf("    ./mixer uart\n");
  Core::DebugPrintf("    ./mixer spi\n");
  Core::DebugPrintf("    ./mixer midi\n");
  Core::DebugPrintf("    ./mixer burnin\n");
  Core::DebugPrintf("    ./mixer ledon\n");
  Core::DebugPrintf("    ./mixer ledoff\n");
  Core::DebugPrintf("******************************\n\n");
}

bool RackPanelComponent::checkMonitorRestore(
    Presonus::DelayTimer &timer) const {
  if (!timer.isLongEnoughYet())
    return false;
  if (savedMonitorValue == 1.f && monitorRadioParameter)
    monitorRadioParameter->setValue(1.f, false);
  return true;
}
void RackPanelComponent::monitorSource(int source, bool enabled) {
  auto &parameters = dependencies().monitorParameters();
  int tag;
  if (source == 4)
    tag = 24;
  else if (source == 5)
    tag = 20;
  else
    return;
  if (auto *p = parameters.getParameterByTag(tag))
    p->setValue(enabled ? 1.f : 0.f, true);
}
void RackPanelComponent::updatePanelStatus() {
  float blue = 0.f, red = 0.f;
  int blinkMode = 0;
  if (panelStatus == 1) {
    red = 1.f;
    blinkMode = 2;
  } else if (panelStatus == 2) {
    blue = 1.f;
    blinkMode = 2;
  } else if (panelStatus == 3) {
    if (dependencies().numClients() == 0)
      blue = 1.f;
    else
      red = 1.f;
  }
  auto *redLED = static_cast<LEDControl *>(
      dependencies().group(0).byTag(100)->castTo(0x4c656443));
  auto *blueLED = static_cast<LEDControl *>(
      dependencies().group(0).byTag(101)->castTo(0x4c656443));
  // As in the original, the required status LEDs and parameters must exist.
  dependencies().blink(*redLED, blinkMode);
  dependencies().blink(*blueLED, blinkMode);
  getParameterByTag(2)->setValue(blue, false);
  getParameterByTag(3)->setValue(red, false);
}
void RackPanelComponent::attachMeterLEDs() {
  Core::DebugPrintf("RackPanelComponent::attachMeterLEDs ()\n");
  const auto &channels = dependencies().channels();
  for (std::size_t i = 0; i < meterLEDs.size(); ++i) {
    auto *parameter = channels.at(i).parameters->getParameterByTag(0x138);
    meterLEDs[i]->setParameter(parameter, 0);
    parameter->setValue(0.f, true);
  }
  for (std::size_t i = 0; i < clipLEDs.size(); ++i)
    clipLEDs[i]->setParameter(
        channels.at(i).parameters->getParameterByTag(0x137), 0);
}
void RackPanelComponent::attach48vControls() {
  auto &group = dependencies().group(3);
  for (const auto &channel : dependencies().channels()) {
    if (group.byTag(channel.tag)) {
      auto *parameter = channel.parameters->getParameterByTag(0x133);
      group.byTag(channel.tag)->setParameter(parameter, 0);
    }
  }
}
void RackPanelComponent::cleanup() {
  dependencies().removeDelegate(*this);
  if (observedParameter)
    observedParameter->removeObserver(this);
}
void RackPanelComponent::attach48vLEDs() {
  Core::DebugPrintf("RackPanelComponent::attach48vLEDs ()\n");
  const auto &channels = dependencies().channels();
  for (std::size_t i = 0; i < phantomLEDs.size(); ++i)
    phantomLEDs[i]->setParameter(
        channels.at(i).parameters->getParameterByTag(0x133), 0);
}
void RackPanelComponent::detachLEDs() {
  Core::DebugPrintf("RackPanelComponent::detachLEDs ()\n");
  for (auto *control : meterLEDs)
    control->setParameter(nullptr, 0);
  for (auto *control : clipLEDs)
    control->setParameter(nullptr, 0);
  for (auto *control : phantomLEDs)
    control->setParameter(nullptr, 0);
}
void RackPanelComponent::setupMonitorRadioButton(int tag) {
  monitorRadioParameter = dependencies().group(0).byTag(tag)->getParameter();
  savedMonitorValue = monitorRadioParameter->getValue();
  if (monitorRadioParameter)
    monitorRadioParameter->setValue(0.f, false);
}
void RackPanelComponent::attachDigipots() {
  auto &group = dependencies().group(1);
  for (const auto &channel : dependencies().channels()) {
    if (auto *control = group.byTag(channel.tag)) {
      control->setParameter(channel.parameters->getParameterByTag(0x13b), 0);
      channel.parameters->getParameterByTag(0x13a)->changed();
    }
  }
}
} // namespace Presonus::Panel
