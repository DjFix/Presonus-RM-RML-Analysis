#include "presonus/surface/AssignEditPageComponent.hpp"
#include <cstring>

namespace Presonus::Surface {
using Core::Portable::AliasParam;
using Core::Portable::Component;
using Core::Portable::Parameter;

AssignEditPageComponent::~AssignEditPageComponent() = default;

void AssignEditPageComponent::updateVisibility() {
  if (!page_ || !page_->isVisible())
    return;

  bool assigned = false;
  auto *buses = mixer_ ? access().channelContainer(mixer_, 4) : nullptr;
  if (buses) {
    for (int index = 0; index < buses->countChildren(); ++index) {
      auto *bus = buses->getChild(index);
      auto *mode = bus ? bus->getParameterByTag(411) : nullptr;
      if (mode && mode->getValue() > 0.f) {
        assigned = true;
        break;
      }
    }
  }
  if (auto *visibility = getParameterByTag(1000))
    visibility->setValue(assigned ? 1.f : 0.f, false);
}

void AssignEditPageComponent::updateAliasTargets() {
  if (!page_ || !page_->isVisible() || !mixer_)
    return;

  auto &mixerAccess = access();
  auto *inputs = mixerAccess.channelContainer(mixer_, 0);
  auto *returns = mixerAccess.channelContainer(mixer_, 2);
  auto *buses = mixerAccess.channelContainer(mixer_, 4);
  if (!inputs || !returns || !buses)
    return;

  auto *slave = mixerAccess.slaveMixer(mixer_);
  auto *slaveInputs = slave ? mixerAccess.channelContainer(slave, 0) : nullptr;
  auto *selected = mixerAccess.selectedChannel(mixer_);
  const bool selectable =
      selected && (inputs->getChildIndex(selected) >= 0 ||
                   (slaveInputs && slaveInputs->getChildIndex(selected) >= 0) ||
                   returns->getChildIndex(selected) >= 0);
  for (int index = 0; index < 16; ++index) {
    Core::CString32 assignName("slot_assign"), modeName("slot_bus_mode"),
        channelName("slot_chname");
    const int slot = index + 1;
    assignName.appendFormat("_%02d", slot);
    modeName.appendFormat("_%02d", slot);
    channelName.appendFormat("_%02d", slot);
    // The represented CCL parameters are actual parameters or aliases.
    auto *assign = AliasParam::cast(findParameter(assignName));
    auto *channelNameAlias = AliasParam::cast(findParameter(channelName));
    auto *mode = AliasParam::cast(findParameter(modeName));
    auto *bus =
        index < buses->countChildren() ? buses->getChild(index) : nullptr;
    auto *channelNameParam = bus ? bus->getParameterByTag(2) : nullptr;
    if (channelNameAlias)
      channelNameAlias->setOriginal(selectable ? channelNameParam : nullptr);
    auto *assignment =
        selectable ? selected->getParameterByTag(255 + slot) : nullptr;
    if (assign)
      assign->setOriginal(assignment);
    auto *busMode = bus ? bus->getParameterByTag(411) : nullptr;
    if (mode)
      mode->setOriginal(busMode);
  }
}

void AssignEditPageComponent::paramChanged(Parameter *parameter, int message) {
  if (message != Parameter::kChanged || !page_ || !page_->isVisible())
    return;

  if (std::strcmp(parameter->getName(), "sel_chnum") == 0)
    updateAliasTargets();
  const char *name = parameter->getName();
  if (std::strstr(name, "slot_bus_mode") == name)
    updateVisibility();
}
} // namespace Presonus::Surface
