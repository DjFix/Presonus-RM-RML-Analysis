#include "presonus/surface_panel/ControlHelpers.hpp"
#include <stdexcept>
namespace Presonus::Surface {
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

#include "core/system/coredebug.h"
#include <limits>
namespace Presonus::Surface {
void SurfaceRootComponent::terminateTestTouchscreen() {
  if (!services_)
    throw std::logic_error("root services required");
  services_->touchscreenActive = false;
  if (!services_->children)
    throw std::logic_error("live children required");
  auto *screen = getMainScreenComponent();
  Core::Portable::Component *component = nullptr;
  for (const auto &reference : services_->mainScreens)
    if (screen && reference.reference == screen &&
        reference.component == services_->children->findChild("mainscreen")) {
      component = reference.component;
      break;
    }
  if (!component || !services_->rootParameters || !services_->observer)
    throw std::logic_error("live root/screen parameters and observer required");
  auto *exit = component->getParameterByTag(38);
  if (!exit)
    throw std::logic_error("screen tag 38 required");
  exit->removeObserver(services_->observer);
  auto *touch = services_->rootParameters->getParameterByTag(903);
  if (!touch)
    throw std::logic_error("root tag 903 required");
  touch->removeObserver(services_->observer);
  if (registrar_)
    registrar_->runTest(static_cast<PanelRegistrar::TestMode>(111), false);
}
void SurfaceRootComponent::manageUtilPageObserver(bool enabled) {
  // Process-shared, just as the original function-local static. Single-threaded
  // application domain. Explicit wrap preserves ARM ADD/SUB without C++ UB.
  static std::int32_t activeTestCount = 0;
  const auto previous = activeTestCount;
  if (enabled) {
    activeTestCount = previous == std::numeric_limits<std::int32_t>::max()
                          ? std::numeric_limits<std::int32_t>::min()
                          : previous + 1;
    if (previous > 0)
      return;
  } else {
    activeTestCount = previous == std::numeric_limits<std::int32_t>::min()
                          ? std::numeric_limits<std::int32_t>::max()
                          : previous - 1;
    if (activeTestCount > 0)
      return;
    if (activeTestCount < 0) {
      Core::DebugPrintf("SurfaceRootComponent::manageUtilPageObserver "
                        "activeTestCount is negative!\n");
      activeTestCount = 0;
    }
  }
  if (!services_ || !services_->observer)
    throw std::logic_error("live root services and observer required");
  if (!services_->children)
    throw std::logic_error("live children required");
  auto *screen = getMainScreenComponent();
  Core::Portable::Component *component = nullptr;
  for (const auto &reference : services_->mainScreens)
    if (screen && reference.reference == screen &&
        reference.component == services_->children->findChild("mainscreen")) {
      component = reference.component;
      break;
    }
  if (!component)
    throw std::logic_error("live main screen component required");
  auto *parameter = component->getParameterByTag(2);
  if (!parameter)
    throw std::logic_error("screen tag 2 required");
  if (enabled)
    parameter->addObserver(services_->observer);
  else
    parameter->removeObserver(services_->observer);
}
} // namespace Presonus::Surface
