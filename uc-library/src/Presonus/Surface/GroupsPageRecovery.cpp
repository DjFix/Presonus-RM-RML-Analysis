#include "presonus/surface/GroupsPageComponent.hpp"
#include <cmath>
#include <cstring>
#include <stdexcept>
namespace Presonus::Surface {
GroupsPageComponent::~GroupsPageComponent() = default;
bool GroupsPageComponent::isAutoGroup(Core::Portable::Component *group) const {
  return group && group->getParent() &&
         std::strcmp(group->getParent()->getName(), "autofiltergroup") == 0;
}
bool GroupsPageComponent::isValidGroup(Core::Portable::Component *group) const {
  // Native requires tag 600 to exist; invalid inputs are outside the domain.
  Core::CString32 text;
  group->getParameterByTag(600)->toString(text.getBuffer(), 32);
  if (text.length())
    return true;
  for (int i = 0; i < group->countParameters(); ++i) {
    auto *p = group->getParameterAt(i);
    if (!p || !p->isStorable())
      continue;
    if (p->getValue() == p->getDefault())
      continue;
    if (!(std::fabs(p->getValue() - p->getDefault()) < 0.00001f))
      return true;
  }
  return false;
}
void GroupsPageComponent::select(Core::Portable::Parameter *p) {
  if (!(p->getValue() > 0.f))
    state.selection = -1;
  else {
    state.selection = presonus::surface::addWrap(
        state.listOffset, state.selectionParameters.index(p));
    const int count = state.selectionParameters.count();
    for (int i = 0; i < count; ++i)
      state.selectionParameters.at(i)->setValue(
          state.selectionParameters.at(i) == p ? 1.f : 0.f, false);
  }
  doselect();
}
Core::Portable::Component *GroupsPageComponent::getSelectedSlaveGroup() const {
  if (!state.observedGroup || !mixer_ || !access().slaveMixer(mixer_))
    return nullptr;
  Core::CString256 path;
  state.observedGroup->getComponentPath(path);
  auto *slave = access().slaveMixer(mixer_);
  auto *root = access().mixerRoot(slave);
  return root ? root->lookupChild(path) : nullptr;
}
void GroupsPageComponent::addRemoveObservers(
    Presonus::MixerClientComponentBase *, bool add) {
  // Native ignores the explicit mixer argument and uses current mixer state.
  for (const char *name : {"filtergroup", "autofiltergroup"}) {
    auto *container = access().groupContainer(mixer_, name);
    if (!container)
      continue;
    for (int i = 0; i < container->countChildren(); ++i) {
      auto *group = container->getChild(i);
      for (int tag : {603, 600})
        if (auto *p = group->getParameterByTag(tag)) {
          if (add)
            p->addObserver(this);
          else
            p->removeObserver(this);
        }
    }
  }
}
void GroupsPageComponent::observeGroup(Core::Portable::Component *group) {
  for (int i = 0; i < observedParameters.count(); ++i)
    observedParameters.at(i)->removeObserver(this);
  observedParameters.resize(0);
  if (group)
    for (int tag = 646; tag < 686; ++tag)
      if (auto *p = group->getParameterByTag(tag)) {
        p->addObserver(this);
        observedParameters.add(p);
      }
}
void GroupsPageComponent::launchEdit() {
  if (mapping_)
    if (auto *p = mapping_->getMainScreenParamByTag(25))
      p->setValue(1.f, true);
}
void GroupsPageComponent::setMixerComponent(
    Presonus::MixerClientComponentBase *p) {
  if (mixer_)
    addRemoveObservers(mixer_, false);
  mixer_ = p;
  if (mixer_)
    addRemoveObservers(mixer_, true);
  // Native removes observers but deliberately retains the list here.
  for (int i = 0; i < observedParameters.count(); ++i)
    observedParameters.at(i)->removeObserver(this);
  state.selection = -1;
}
void GroupsPageComponent::updateGroups(Core::Portable::Component *selected) {
  if (!mixer_)
    return;
  groups[0].resize(0);
  groups[1].resize(0);
  const auto *show = findParameter("show_auto");
  const bool automatic = show && show->getValue() > 0.f;
  bool found = false;
  int ordinal = 0;
  for (int which = 0; which < 2; ++which) {
    if (which == 1 && !automatic)
      continue;
    auto *container = access().groupContainer(mixer_, which ? "autofiltergroup"
                                                            : "filtergroup");
    if (!container)
      continue;
    for (int i = 0; i < container->countChildren(); ++i) {
      auto *group = container->getChild(i);
      if (isValidGroup(group))
        groups[which].add(group);
      // Native ordinal includes invalid groups; preserve that distinction.
      if (selected == group) {
        found = true;
        state.selection = ordinal;
        state.observedGroup = group;
      }
      ++ordinal;
    }
  }
  state.firstGroups = Core::ConstVector<Core::Portable::Component *>(
      groups[0].getItems(), groups[0].count());
  state.secondGroups = Core::ConstVector<Core::Portable::Component *>(
      groups[1].getItems(), groups[1].count());
  if (previousCounts[0] != groups[0].count() ||
      previousCounts[1] != groups[1].count()) {
    previousCounts[0] = groups[0].count();
    previousCounts[1] = groups[1].count();
    if (!selected)
      state.selection = -1;
  }
  if (found &&
      (state.selection < state.listOffset ||
       state.selection > presonus::surface::addWrap(state.listOffset, 7)))
    setListOffset(state.selection);
}
void GroupsPageComponent::refreshList() {
  if (!page_)
    throw std::logic_error("real PageComponent visibility binding required");
  if (!page_->isVisible())
    return;
  updateGroups(nullptr);
  const int maximum = getMaxListOffset();
  if (state.listOffset > maximum)
    state.listOffset = maximum;
  for (int i = 0; i < 8; ++i) {
    auto *label = getParameterByTag(101 + i * 102);
    auto *button = getParameterByTag(100 + i * 102);
    button->enable(true);
    const int ordinal = presonus::surface::addWrap(state.listOffset, i);
    Core::Portable::Component *group = nullptr;
    int index = ordinal;
    const Core::ConstVector<Core::Portable::Component *> *list =
        &state.firstGroups;
    if (index >= list->count()) {
      index -= list->count();
      list = &state.secondGroups;
    }
    if (index >= 0 && index < list->count())
      group = list->at(index);
    Core::CString32 text;
    if (group) {
      if (auto *name = group->getParameterByTag(600))
        name->toString(text.getBuffer(), 32);
    } else
      button->enable(false);
    label->fromString(text, false);
    button->setValue(state.selection == ordinal ? 1.f : 0.f, false);
  }
}
} // namespace Presonus::Surface

namespace Presonus::Surface {
void GroupsPageComponent::updateFilter() {
  if (!state.observedGroup)
    return;
  for (int i = 0; i < 39; ++i)
    if (auto *p = state.observedGroup->getParameterByTag(646 + i))
      groupFilters[0].setVisible(i, p->getValue() > 0.f);
  auto *slave = getSelectedSlaveGroup();
  if (!slave)
    return;
  for (int i = 0; i < 32; ++i)
    if (auto *p = slave->getParameterByTag(646 + i))
      groupFilters[1].setVisible(i, p->getValue() > 0.f);
}
void GroupsPageComponent::doselect() {
  const bool selected = state.selection >= 0;
  auto *enabled = getParameterByTag(1008);
  if (!enabled)
    throw std::logic_error("Groups selection parameter1008 required");
  enabled->setValue(selected ? 1.f : 0.f, false);
  updateSelection();
  updateFilter();
  if (auto *p = getParameterByTag(1009))
    p->setValue(isAutoGroup(state.observedGroup) ? 0.f : 1.f, false);
  if (mixer_) {
    access().setFilter(mixer_, selected ? &groupFilters[0] : nullptr);
    if (auto *slave = access().slaveMixer(mixer_))
      access().setFilter(slave, selected ? &groupFilters[1] : nullptr);
    access().setSelectedGroup(mixer_, state.observedGroup);
  }
  if (!mapping_)
    return;
  auto *mode = mapping_->getParamByTag(6);
  const bool modeActive = mode && mode->getValue() > 0.f;
  const bool groupActive = mixer_ && selected && state.observedGroup;
  for (int i = 0; i < 5; ++i) {
    auto *p = mapping_->getParamByTag(i);
    if (p && p->getValue() > 0.f) {
      if (groupActive)
        p->setValue(0.f, false);
      p->performEdit();
      return;
    }
  }
  if (auto *p = mapping_->getParamByTag(0)) {
    if (!groupActive && !modeActive)
      p->setValue(1.f, false);
    p->performEdit();
  }
}
} // namespace Presonus::Surface
