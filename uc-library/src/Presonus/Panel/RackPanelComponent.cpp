#include "presonus/panel/RackPanelComponent.hpp"
#include "core/system/coredebug.h"
namespace Presonus::Panel {
bool RackPanelComponent::checkMonitorRestore(
    Presonus::DelayTimer &timer) const {
  if (!timer.isLongEnoughYet())
    return false;
  if (savedMonitorValue == 1.f && monitorRadioParameter)
    monitorRadioParameter->setValue(1.f, false);
  return true;
}
void RackPanelComponent::monitorSource(int source, bool enabled) {
  auto &parameters = deps.monitorParameters();
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
    if (deps.numClients() == 0)
      blue = 1.f;
    else
      red = 1.f;
  }
  auto *redLED =
      static_cast<LEDControl *>(deps.group(0).byTag(100)->castTo(0x4c656443));
  auto *blueLED =
      static_cast<LEDControl *>(deps.group(0).byTag(101)->castTo(0x4c656443));
  // As in the original, the required status LEDs and parameters must exist.
  deps.blink(*redLED, blinkMode);
  deps.blink(*blueLED, blinkMode);
  getParameterByTag(2)->setValue(blue, false);
  getParameterByTag(3)->setValue(red, false);
}
void RackPanelComponent::attachMeterLEDs() {
  Core::DebugPrintf("RackPanelComponent::attachMeterLEDs ()\n");
  const auto &channels = deps.channels();
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
  auto &group = deps.group(3);
  for (const auto &channel : deps.channels()) {
    if (group.byTag(channel.tag)) {
      auto *parameter = channel.parameters->getParameterByTag(0x133);
      group.byTag(channel.tag)->setParameter(parameter, 0);
    }
  }
}
void RackPanelComponent::cleanup() {
  deps.removeDelegate(*this);
  if (observedParameter)
    observedParameter->removeObserver(this);
}
void RackPanelComponent::attach48vLEDs() {
  Core::DebugPrintf("RackPanelComponent::attach48vLEDs ()\n");
  const auto &channels = deps.channels();
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
  monitorRadioParameter = deps.group(0).byTag(tag)->getParameter();
  savedMonitorValue = monitorRadioParameter->getValue();
  if (monitorRadioParameter)
    monitorRadioParameter->setValue(0.f, false);
}
void RackPanelComponent::attachDigipots() {
  auto &group = deps.group(1);
  for (const auto &channel : deps.channels()) {
    if (auto *control = group.byTag(channel.tag)) {
      control->setParameter(channel.parameters->getParameterByTag(0x13b), 0);
      channel.parameters->getParameterByTag(0x13a)->changed();
    }
  }
}
} // namespace Presonus::Panel
