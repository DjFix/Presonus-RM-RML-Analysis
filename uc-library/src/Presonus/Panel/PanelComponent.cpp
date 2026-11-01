#include "presonus/panel/PanelComponent.hpp"
namespace Presonus::Panel {
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
void PanelComponent::activateAll() { services.componentSlot38(); }
void PanelComponent::blinkLed(int group, int tag, bool blink) {
  void *control = services.byTag(services.findGroup(group), tag);
  if (!control)
    return;
  if (void *led = services.castControlToLed(control))
    services.setBlinkMode(led, blink ? 2 : 0);
}
} // namespace Presonus::Panel
