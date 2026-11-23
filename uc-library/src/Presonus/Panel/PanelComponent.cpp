#include "presonus/panel/PanelComponent.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
namespace Presonus::Panel {
void PanelComponent::onIdle() {
  portable.component.Core::Portable::Component::onIdle();
}
void PanelComponent::paramChanged(Core::Portable::Parameter *parameter,
                                  int message) {
  portable.component.Core::Portable::Component::paramChanged(parameter,
                                                             message);
}
void PanelComponent::detachGroup(const ControlGroup &group) const {
  const int count = services.controlCount(group);
  for (int i = 0; i < count; ++i)
    if (void *control = services.controlAt(group, i))
      services.controlSlot10(control, 0, 0);
}
void PanelComponent::detachAll() const {
  const int count = services.groupCount();
  for (int i = 0; i < count; ++i)
    detachGroup(services.groupAt(i));
}
void PanelComponent::detachSwitches() const {
  const int count = services.groupCount();
  for (int i = 0; i < count; ++i) {
    const auto &group = services.groupAt(i);
    auto tag = services.groupTag(group);
    if (tag <= 11 && ((1u << tag) & 4079u))
      detachGroup(group);
  }
}
void PanelComponent::start() { activateAll(); }
void PanelComponent::activateAll() { services.componentSlot38(); }
bool PanelComponent::isInGroup(
    int groupId, const Core::Portable::Parameter &parameter) const {
  if (!controlRegistrar)
    throw std::logic_error("PanelComponent control registrar is not bound");
  for (int groupIndex = 0; groupIndex < controlRegistrar->count();
       ++groupIndex) {
    const auto &group = *controlRegistrar->at(groupIndex);
    if (presonus::panel_binding::ControlGroupAccess::groupId(group) != groupId)
      continue;
    for (int controlIndex = 0; controlIndex < group.count(); ++controlIndex)
      if (group.at(controlIndex)->getParameter() == &parameter)
        return true;
    return false;
  }
  return false;
}
void PanelComponent::doActivate() {}
void PanelComponent::cleanup() {}
void PanelComponent::blinkLed(int group, int tag, bool blink) {
  void *control = services.byTag(services.findGroup(group), tag);
  if (!control)
    return;
  if (void *led = services.castControlToLed(control))
    services.setBlinkMode(led, blink ? 2 : 0);
}
} // namespace Presonus::Panel

#include "core/public/corestringbuffer.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
namespace Presonus::Panel {
void PanelComponent::init() {
  Core::CString64 description;
  description.appendFormat("%d",
                           portable.registrar->sourcePortDescriptionNumber());
  if (auto *p = portable.mixer->sceneSettings->getParameterByTag(0))
    p->fromString(description, false);
}
} // namespace Presonus::Panel
