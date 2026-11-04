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
