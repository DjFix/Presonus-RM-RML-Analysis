#include "presonus/surface/GroupsEditPageComponent.hpp"
#include "core/public/corestringbuffer.h"
#include <cstdint>

namespace {
std::int32_t wrappedAdd(std::int32_t left, std::int32_t right) {
  const auto value =
      static_cast<std::uint32_t>(left) + static_cast<std::uint32_t>(right);
  // Preserve the observed 32-bit arithmetic without signed-overflow UB.
  return value <= 0x7fffffffU ? static_cast<std::int32_t>(value)
                              : -1 - static_cast<std::int32_t>(~value);
}
} // namespace

namespace Presonus::Surface {
void GroupsEditPageComponent::buildItemsList() {
  if (!state.mixerAvailable)
    return;
  const auto selection = dependencies.findGroupsPage();
  if (!selection.group)
    return;
  if (dependencies.hasSlaveMixer() && !selection.slaveGroup)
    return;
  state.items.resize(0);
  const auto append = [&](const char *name, bool slave,
                          Core::Portable::Component *group, int firstTag) {
    const auto channels = dependencies.components(name, slave);
    for (int index = 0; index < channels.count(); ++index)
      state.items.add({channels[index], group, firstTag + index});
  };
  append("line", false, selection.group, 646);
  if (dependencies.hasSlaveMixer()) {
    // The original queries the slave again before obtaining its root/list.
    dependencies.hasSlaveMixer();
    append("line", true, selection.slaveGroup, 646);
  }
  append("fxreturn", false, selection.group, 678);
  append("return", false, selection.group, 682);
}

void GroupsEditPageComponent::paramChanged(Core::Portable::Parameter *parameter,
                                           int message) {
  if (message != Core::Portable::Parameter::kEdit)
    return;
  switch (parameter->getTag()) {
  case 1002:
    parameter->resetValue(false);
    deleteGroup();
    break;
  case 1003:
    if (parameter->getValue() > 0.f)
      addListOffset(-4);
    break;
  case 1004:
    if (parameter->getValue() > 0.f)
      addListOffset(4);
    break;
  case 1006:
    rename();
    break;
  default:
    break;
  }
}

void GroupsEditPageComponent::updateFilterAssignments() {
  if (!state.mixerAvailable)
    return;
  const int maximum = getMaxListOffset();
  if (state.listOffset > maximum)
    state.listOffset = maximum;
  int index = state.listOffset;
  const AssignItem empty;
  for (int slot = 1; slot <= 16; ++slot, index = wrappedAdd(index, 1)) {
    Core::CString32 slotName("assign_slot");
    Core::CString32 nameName("assign_slot_name");
    slotName.appendFormat("_%02d", slot);
    nameName.appendFormat("_%02d", slot);
    auto *assignment = Core::Portable::AliasParam::cast(
        dependencies.findParameter(slotName.str()));
    auto *name = Core::Portable::AliasParam::cast(
        dependencies.findParameter(nameName.str()));
    const auto &item =
        index >= 0 && index < state.items.count() ? state.items[index] : empty;
    // CCL 5.0.0 requires a nonnull Component receiver. The native null item
    // boundary is adapted explicitly rather than calling a method on nullptr.
    auto *channelName =
        item.channel ? item.channel->getParameterByTag(1) : nullptr;
    if (name)
      name->setOriginal(channelName);
    if (assignment) {
      if (item.group)
        assignment->setOriginal(item.group->getParameterByTag(item.tag));
      assignment->enable(channelName != nullptr);
    }
  }
}

int GroupsEditPageComponent::getMaxListOffset() const {
  return wrappedAdd(state.items.count(), -16);
}

void GroupsEditPageComponent::textInputFinished(bool) {
  auto *input = state.parameters.byTag(1007);
  auto *name = dependencies.findParameter("group_name");
  if (!input || !name)
    return;
  Core::CString32 text;
  input->toString(text.getBuffer(), text.getSize());
  name->fromString(text.str(), true);
}

void GroupsEditPageComponent::setListOffset(int offset) {
  if (offset < 0)
    offset = 0;
  else if (offset >= getMaxListOffset())
    offset = getMaxListOffset();
  if (state.listOffset == offset)
    return;
  state.listOffset = offset;
  updateFilterAssignments();
}

void GroupsEditPageComponent::deleteGroup() {
  const auto selection = dependencies.findGroupsPage();
  if (selection.group)
    selection.group->resetToDefaults(false, true, nullptr);
  if (selection.page)
    selection.page->deSelect();
  if (state.navigation)
    if (auto *parameter = state.navigation->getParameterByTag(24))
      parameter->setValue(1.f, true);
}

void GroupsEditPageComponent::addListOffset(int delta) {
  setListOffset(wrappedAdd(state.listOffset, delta));
}

void GroupsEditPageComponent::rename() {
  auto *input = state.parameters.byTag(1007);
  if (!input)
    return;
  auto *name = dependencies.findParameter("group_name");
  if (!name)
    return;
  Core::CString32 text;
  name->toString(text.getBuffer(), text.getSize());
  input->fromString(text.str(), false);
  dependencies.startTextInput(input, "Rename Group:", *this);
}

void GroupsEditPageComponent::onShow(bool visible) {
  dependencies.pageOnShow(visible);
  if (!dependencies.page().isVisible())
    return;
  state.listOffset = 0;
  const auto selection = dependencies.findGroupsPage();
  buildItemsList();
  updateFilterAssignments();
  auto *name =
      selection.group ? selection.group->getParameterByTag(600) : nullptr;
  dependencies.connect("page:groupsedit.group_name", name);
}
} // namespace Presonus::Surface
