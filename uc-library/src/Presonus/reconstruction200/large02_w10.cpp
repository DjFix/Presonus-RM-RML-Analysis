#include "presonus/reconstruction200/large02_w10.hpp"
namespace Presonus::Surface {
// Source-port declaration only; native return and storage layout unresolved.
// Native passes tag 1000, converts unsigned-short progress to float, and
// dispatches Parameter::setValue with update=false. Panel argument is unused.
void PanelRegistrar::handleCalibrateTouchscreenProgress(
    unsigned char, unsigned short progress) {
  parameters_->byTag(1000)->setValue(static_cast<float>(progress), false);
}
} // namespace Presonus::Surface
#include "core/system/coredebug.h"
#include "presonus/surface_panel/OutputPin.hpp"
#include <stdexcept>
namespace {
void send(presonus::surface::RegistrarTestState &state, unsigned char a,
          unsigned char b, unsigned char c, unsigned char d) {
  Uart_Msg_Type message{{a, b, c, d}};
  state.services.send(state.services.context, message);
}
constexpr unsigned char rgbAddresses[48] = {
    0, 0,  0,  1,  0,  2,  0,  3,  0,  4,  0,  5,  0,  6,  0,  7,
    0, 8,  0,  9,  0,  10, 0,  11, 0,  12, 0,  13, 0,  14, 0,  15,
    0, 18, 10, 29, 10, 30, 10, 31, 10, 32, 10, 33, 10, 35, 10, 37};
} // namespace
namespace Presonus::Surface {
void PanelRegistrar::setColorRgbLeds(unsigned char color) {
  for (int i = 0; i < 48; i += 2) {
    Uart_Msg_Type message{{114, rgbAddresses[i], rgbAddresses[i + 1], color}};
    getPort()->writeMsg(message);
  }
}
void PanelRegistrar::turnOnRgbLeds(bool enabled) {
  for (int i = 0; i < 48; i += 2) {
    Uart_Msg_Type message{{76, rgbAddresses[i], rgbAddresses[i + 1],
                           static_cast<unsigned char>(enabled)}};
    getPort()->writeMsg(message);
  }
}
void PanelRegistrar::invokePanelTest(TestMode mode, bool enabled) {
  unsigned value = 0;
  switch (static_cast<int>(mode)) {
  case 100:
    value = enabled;
    break;
  case 101:
    value = 2;
    break;
  case 102:
    value = 3;
    break;
  case 103:
    value = 4;
    break;
  case 104:
    value = 5;
    break;
  }
  send(*tests_, 103, 13, static_cast<unsigned char>(value), 0);
}
void PanelRegistrar::invoke48vTest(bool enabled) {
  send(*tests_, 77, 0, enabled, 0);
  send(*tests_, 77, 1, enabled, 0);
}
void PanelRegistrar::invokeCalibrateTouchTest(bool enabled) {
  Core::DebugPrintf(enabled ? "      PanelRegistrar::invokeCalibrateTouchTest "
                              "start calibrate test\n"
                            : "     PanelRegistrar::invokeCalibrateTouchTest "
                              "end calibrate test\n");
  if (enabled)
    parameters_->byTag(1000)->setValue(0, false);
  send(*tests_, 103, 12, enabled, 0);
}
void PanelRegistrar::invokeTestTouchscreen(bool enabled) {
  if (enabled) {
    parameters_->byTag(903)->setValue(0, false);
    parameters_->byTag(2001)->setValue(0, false);
    tests_->touchTimer.beginAction(2);
  } else
    tests_->touchTimer.endAction();
  tests_->touchscreen = enabled;
}
void PanelRegistrar::invokeScribbleStripTest(bool enabled) {
  Core::DebugPrintf(
      enabled ? "PanelRegistrar::invokeScribbleStripTest starting test\n"
              : "PanelRegistrar::invokeScribbleStripTest ending test\n");
  tests_->scribble = enabled;
  if (enabled) {
    parameters_->byTag(2000)->setValue(0, false);
    tests_->scribbleTimer.beginAction(3);
  } else
    tests_->scribbleTimer.endAction();
}
void PanelRegistrar::invokeRgbTest(bool enabled) {
  Core::DebugPrintf("PanelRegistrar::invokeRgbTest\n");
  tests_->rgb = enabled;
  if (enabled) {
    tests_->rgbTimer.beginAction(3);
    tests_->color = 0;
    setColorRgbLeds(0);
    turnOnRgbLeds(true);
  } else {
    tests_->rgbTimer.endAction();
    turnOnRgbLeds(false);
  }
}
void PanelRegistrar::invokeControlSurfaceTest(bool enabled) {
  Core::DebugPrintf(
      enabled ? "PanelRegistrar::invokeControlSurfaceTest Start test\n"
              : "PanelRegistrar::invokeControlSurfaceTest Stop test\n");
  tests_->controls = enabled;
  tests_->services.testMode(tests_->services.context, enabled);
  if (enabled) {
    tests_->controlValues.fill(0);
    tests_->switchValues.fill(0);
    send(*tests_, 86, 255, 0, 0);
  }
}
void PanelRegistrar::runTest(TestMode mode, bool enabled) {
  Core::DebugPrintf("PanelRegistrar::runTest: %s test mode %d\n",
                    enabled ? "starting" : "stopping", static_cast<int>(mode));
  switch (static_cast<int>(mode)) {
  case 100:
  case 101:
  case 102:
  case 103:
  case 104:
    invokePanelTest(mode, enabled);
    break;
  case 105:
    invokeScribbleStripTest(enabled);
    break;
  case 106:
    invokeCalibrateTouchTest(enabled);
    break;
  case 107:
    invokeFaderCalibration(enabled);
    break;
  case 108:
    invokeControlSurfaceTest(enabled);
    break;
  case 109:
    invokeRgbTest(enabled);
    break;
  case 110:
    invoke48vTest(enabled);
    break;
  case 111:
    invokeTestTouchscreen(enabled);
    break;
  }
}
void PanelRegistrar::handleTouchscreen(Touchscreen_Type &message) {
  if (!tests_->touchscreen)
    tests_->services.touchscreen(tests_->services.context, message);
  else if (*reinterpret_cast<const unsigned char *>(&message) == 84)
    parameters_->byTag(903)->setValue(1, false);
}
Core::Portable::Parameter *
PanelRegistrar::findParameter(const char *name) const {
  return parameters_->find(name);
}
Core::Portable::Parameter *PanelRegistrar::getParameterByTag(int tag) const {
  return parameters_->byTag(tag);
}
void PanelRegistrar::addSwitchControlGroup(
    int group, const Core::Portable::ParamInfo *info, int count) {
  auto controls = std::make_unique<Presonus::Panel::ControlGroup>(group, count);
  for (int i = 0; i < count; ++i) {
    auto control = std::make_unique<Presonus::Panel::SwitchControl>(
        info[i].tag, group, true);
    control->setIO(tests_->services.io);
    controls->add(control.get());
    tests_->switches.push_back(std::move(control));
  }
  // Source-port ownership is explicit. Native registration capacity is 32;
  // caller domain excludes capacity exhaustion and allocation failure.
  if (tests_->groups.size() < 32)
    tests_->groups.push_back(std::move(controls));
}
void PanelRegistrar::adjustLcdBrightness(int brightness) {
  Presonus::Panel::OutputPin output(97);
  output.set(brightness);
}
int SurfaceRootComponent::bumpFaderSpeed(int delta) {
  return registrar_ ? registrar_->bumpFaderSpeed(delta) : 0;
}
int SurfaceRootComponent::bumpFaderTouchSensitivity(int delta) {
  return registrar_ ? registrar_->bumpFaderTouchSensitivity(delta) : 0;
}
void SurfaceRootComponent::paramChangedLcdBrightness(
    Core::Portable::Parameter *parameter) {
  registrar_->adjustLcdBrightness(static_cast<int>(parameter->getValue()));
}
} // namespace Presonus::Surface

namespace Presonus::Surface {
void SurfaceRootComponent::updateFocusParams(
    Presonus::Panel::Control *control) {
  if (!control || !services_ || !services_->focus)
    return;
  auto *parameter = control->getParameter();
  if (!parameter)
    return;
  // Scope-safe source-port inlining of PageHeaderComponent::updateFocusParam,
  // original dependency symbol/range retained separately; no helper admission.
  auto &state = *services_->focus;
  if (!state.alias || !state.label)
    return;
  auto *original = parameter->getOriginal();
  if (!original || original == state.alias->getOriginal())
    return;
  if (!state.handlers)
    throw std::logic_error("live assignment handler list required");
  Presonus::MixerAssignmentHandler::FocusInfo info;
  // Scope-safe inlining of original AssignmentHandlerTable::getParamFocusInfo.
  // Original helper identities/ranges stay dependency evidence, never credits.
  const int count = state.handlers->count();
  bool found = false;
  for (int index = 0; index < count; ++index) {
    auto *handler = state.handlers->at(index);
    if (!handler)
      continue;
    auto *mixer = static_cast<Presonus::MixerAssignmentHandler *>(
        handler->castTo(0x4d784173));
    if (mixer && mixer->getParamFocusInfo(info, original)) {
      found = true;
      break;
    }
  }
  if (!found)
    return;
  state.alias->setOriginal(info.sourcePort.alternateOriginal
                               ? info.sourcePort.alternateOriginal
                               : original);
  state.label->fromString(info.sourcePort.label, false);
}
void SurfaceRootComponent::faderChanged(
    const Presonus::Panel::ControlRegistrar &, int, int,
    Presonus::Panel::FaderControl *control) {
  updateFocusParams(control);
}
void SurfaceRootComponent::switchChanged(
    const Presonus::Panel::ControlRegistrar &, int, int, bool pressed,
    Presonus::Panel::SwitchControl *control) {
  if (pressed)
    updateFocusParams(control);
}
MainScreenComponent *SurfaceRootComponent::getMainScreenComponent() const {
  auto *component = services_->children->findChild("mainscreen");
  if (!component)
    return nullptr;
  for (const auto &reference : services_->mainScreens) {
    if (reference.component == component &&
        reference.elfSha256 == "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a"
                               "980d855ec5aa449a0" &&
        reference.nativeType ==
            "_ZTIN8Presonus7Surface19MainScreenComponentE" &&
        reference.nativeTypeAddress == 0x1a0434)
      return reference.reference;
  }
  return nullptr;
}
} // namespace Presonus::Surface
