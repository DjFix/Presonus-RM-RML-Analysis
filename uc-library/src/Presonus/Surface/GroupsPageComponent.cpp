#include "presonus/surface/GroupsPageComponent.hpp"
#include <cstring>

namespace {
std::int32_t signedBits(std::uint32_t bits) {
  std::int32_t result;
  std::memcpy(&result, &bits, sizeof result);
  return result;
}
} // namespace
namespace Presonus::Surface {
void GroupsPageComponent::addListOffset(int delta) {
  setListOffset(signedBits(static_cast<std::uint32_t>(delta) +
                           static_cast<std::uint32_t>(state.listOffset)));
}
int GroupsPageComponent::getMaxListOffset() const {
  std::uint32_t bits = static_cast<std::uint32_t>(state.firstGroups.count()) +
                       static_cast<std::uint32_t>(state.secondGroups.count()) -
                       7;
  bits = (bits + (bits >> 31)) & ~std::uint32_t{1};
  return signedBits(bits) < 0 ? 0 : signedBits(bits);
}
void GroupsPageComponent::setListOffset(int offset) {
  int bounded = 0;
  if (offset >= 0) {
    int maximum = getMaxListOffset();
    bounded = offset < maximum ? offset : maximum;
  }
  // Native compares before rounding: an odd request can refresh unchanged
  // state.
  if (state.listOffset == bounded)
    return;
  auto bits = static_cast<std::uint32_t>(bounded);
  state.listOffset = signedBits((bits + (bits >> 31)) & ~std::uint32_t{1});
  dependencies.refreshList();
}
void GroupsPageComponent::deSelect() {
  const int count = state.selectionParameters.count();
  for (int i = 0; i < count; ++i)
    state.selectionParameters.at(i)->setIntValue(0, true);
  state.selection = -1;
  dependencies.doselect();
}
void GroupsPageComponent::updateSelection() {
  Core::Portable::Component *group = nullptr;
  const int index = state.selection;
  if (index >= 0) {
    if (index < state.firstGroups.count())
      group = state.firstGroups.at(index);
    else {
      const auto relative =
          signedBits(static_cast<std::uint32_t>(index) -
                     static_cast<std::uint32_t>(state.firstGroups.count()));
      group = state.secondGroups.at(relative);
    }
  }
  if (state.observedGroup != group)
    dependencies.observeGroup(group);
  state.observedGroup = group;
}
} // namespace Presonus::Surface
