#include "presonus/surface/GroupsPageComponent.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>

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
  refreshList();
}
void GroupsPageComponent::deSelect() {
  const int count = state.selectionParameters.count();
  for (int i = 0; i < count; ++i)
    state.selectionParameters.at(i)->setIntValue(0, true);
  state.selection = -1;
  doselect();
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
    observeGroup(group);
  state.observedGroup = group;
}
} // namespace Presonus::Surface

namespace Presonus::Surface {
void GroupsPageComponent::selectGroup(Core::Portable::Component *group) {
  state.selection = -1;
  updateGroups(nullptr);
  int base = 0;
  for (const auto *list : {&state.firstGroups, &state.secondGroups}) {
    for (int index = 0; index < list->count(); ++index) {
      if (list->at(index) == group) {
        state.selection = presonus::surface::addWrap(base, index);
        break;
      }
    }
    if (state.selection >= 0)
      break;
    base = presonus::surface::addWrap(base, list->count());
  }
  if (state.selection < state.listOffset ||
      state.selection > presonus::surface::addWrap(state.listOffset, 8))
    setListOffset(state.selection);
  doselect();
  refreshList();
}

void GroupsPageComponent::paramChanged(Core::Portable::Parameter *parameter,
                                       int message) {
  using Core::Portable::Parameter;
  if (parameter->getController() !=
      static_cast<Core::Portable::IParamObserver *>(this)) {
    onObserveredParamChange(parameter, message);
    return;
  }
  Core::Portable::Component::paramChanged(parameter, message);
  if (message == Parameter::kChanged) {
    const char *name = parameter->getName();
    if (std::strstr(name, "input_bank") == name && parameter->getValue() > 0.f)
      deSelect();
    if (std::strcmp(name, "show_auto") == 0) {
      if (state.selection >= 0)
        deSelect();
      refreshList();
    }
    return;
  }
  if (message != Parameter::kEdit)
    return;
  if (state.selectionParameters.index(parameter) >= 0)
    select(parameter);
  switch (parameter->getTag()) {
  case 1000:
    if (isAutoGroup(state.observedGroup))
      addGroup(state.observedGroup);
    launchEdit();
    break;
  case 1001:
    addGroup(nullptr);
    if (auto *mode = getParameterByTag(1009))
      mode->setValue(0.f, false);
    launchEdit();
    break;
  case 1003:
    if (parameter->getValue() > 0.f)
      addListOffset(-2);
    break;
  case 1004:
    if (parameter->getValue() > 0.f)
      addListOffset(2);
    break;
  }
}

void GroupsPageComponent::onObserveredParamChange(
    Core::Portable::Parameter *parameter, int message) {
  using namespace Core::Portable;
  if (message != Parameter::kChanged)
    return;
  const int tag = parameter->getTag();
  if (tag == 603 && parameter->getValue() > 0.f) {
    for (const char *name : {"filtergroup", "autofiltergroup"}) {
      auto *container = access().groupContainer(mixer_, name);
      if (!container)
        continue;
      for (int index = 0; index < container->countChildren(); ++index)
        if (auto *selected = container->getChild(index)->getParameterByTag(603))
          selected->setValue(0.f, false);
    }
    selectGroup(core_cast<Component>(parameter->getController()));
    if (mapping_)
      if (auto *mode = mapping_->getParamByTag(6))
        mode->setValue(0.f, true);
  }
  if (tag == 600) {
    if (!page_)
      throw std::logic_error("real PageComponent visibility binding required");
    if (page_->isVisible())
      refreshList();
  } else if (tag >= 646 && tag <= 685)
    doselect();
}

void GroupsPageComponent::addGroup(Core::Portable::Component *source) {
  using namespace Core::Portable;
  auto *container = access().groupContainer(mixer_, "filtergroup");
  if (container)
    for (int index = 0; index < container->countChildren(); ++index) {
      auto *target = container->getChild(index);
      if (!target)
        continue;
      auto *name = target->getParameterByTag(600);
      if (!name)
        continue;
      Core::CString32 text;
      name->toString(text.getBuffer(), 32);
      if (text.length())
        continue;
      Core::CString32 newName("New Filter Group");
      if (source) {
        Core::CString32 original;
        if (auto *sourceName = source->getParameterByTag(600))
          sourceName->toString(original.getBuffer(), 32);
        if (original.getBuffer()[0] == '~') {
          const auto size = std::strlen(original.getBuffer());
          std::memmove(original.getBuffer(), original.getBuffer() + 1, size);
        }
        newName = original;
        const auto available = 31 - std::strlen(newName.getBuffer());
        if (available)
          std::strncat(newName.getBuffer(), ".user",
                       std::min<std::size_t>(available, 5));
        newName.getBuffer()[31] = 0;
        name->fromString(newName, true);
        for (int i = 0; i < source->countParameters(); ++i) {
          auto *from = source->getParameterAt(i);
          auto *to = target->getParameterAt(i);
          if (from && to && from->getType() != ParamInfo::kString)
            to->setValue(from->getValue(), true);
        }
      } else
        name->fromString(newName, true);
      updateGroups(target);
      return;
    }
  updateGroups(nullptr);
}
} // namespace Presonus::Surface
