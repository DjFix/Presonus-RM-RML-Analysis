#include "presonus/surface/GroupsPageComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
using namespace Core::Portable;
static void *watched = nullptr;
static int deletions = 0;
static bool allocationLive = true;
void operator delete(void *p) noexcept {
  if (p == watched && p) {
    ++deletions;
    allocationLive = false;
  }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
struct Deps : presonus::surface::GroupsPageDependencies {
  int selectCalls = 0;
  void refreshList() override {}
  void doselect() override { ++selectCalls; }
  void observeGroup(Component *) override {}
};
struct PageBindings : presonus::page::Bindings {
  const void *visible = nullptr;
  void *castOwner(void *, int) const override {
    return visible ? const_cast<PageBindings *>(this) : nullptr;
  }
  const void *currentPage(void *) const override { return visible; }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};
struct Access : presonus::surface::BorrowedMixerPageAccess {
  Presonus::MixerClientComponentBase primary, secondary;
  presonus::surface::MixerPageView mainView, slaveView;
  Component groupTree;
  presonus::surface::MixerSelectionView mainSelection, slaveSelection;
  Access() {
    mainView.identity = &primary;
    slaveView.identity = &secondary;
    mainView.selectionState = &mainSelection;
    slaveView.selectionState = &slaveSelection;
    for (auto *v : {&mainView, &slaveView}) {
      v->groupTree = &groupTree;
      v->root = nullptr;
      v->slave = nullptr;
      v->selected = nullptr;
      for (auto &c : v->channels)
        c = nullptr;
      registerView(*v);
    }
  }
  void containers(Component *user, Component *automatic) {
    if (user) {
      user->setName("filtergroup");
      groupTree.addChild(user);
    }
    if (automatic) {
      automatic->setName("autofiltergroup");
      groupTree.addChild(automatic);
    }
  }
};
struct Mapping : Presonus::IMappingController {
  Parameter *main = nullptr;
  Parameter *radios[7] = {};
  int getModifiers() const override { return 0; }
  int getRadioValue(int, int) const override { return 0; }
  int getBankScrollingOffset() const override { return 0; }
  Parameter *getParamByTag(int tag) const override {
    return tag >= 0 && tag < 7 ? radios[tag] : nullptr;
  }
  Parameter *getMainScreenParamByTag(int tag) const override {
    if (tag != 25)
      std::abort();
    return main;
  }
  bool isDisplayEncoderLocked() const override { return false; }
  bool areFadersLockedToMainMix() const override { return false; }
  void encoderChanged(int) const override {}
  void onSelectedChannelChanged() override {}
  void selectedChannelUpdated() override {}
  void setRadioGroup(int, int, int, bool) override {}
  void onDeviceDisconnected() override {}
};
ParamInfo info(int tag = 0, int flags = 0) {
  ParamInfo i;
  i.clear();
  i.type = ParamInfo::kFloat;
  i.tag = tag;
  i.minValue = -100;
  i.maxValue = 100;
  i.flags = flags;
  return i;
}
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int id = std::atoi(argv[1]), variant = std::atoi(argv[2]);
  Access access;
  Deps deps;
  PageBindings pb;
  Presonus::PageComponent page(&pb, pb);
  presonus::surface::GroupsPageState state;
  Presonus::Surface::GroupsPageComponent groups(state, deps);
  groups.bindAccess(access);
  groups.bindPage(page);
  Presonus::Surface::SubAssignPageComponent sub(&access, &page);
  const auto mix = &access.primary;
  Mapping mapping;
  const auto map = &mapping;
  auto feedbackInfo = info(1008);
  groups.addParameters(&feedbackInfo, 1, true);
  std::vector<int> out;
  switch (id) {
  case 1:
    sub.setMixerComponent(variant ? mix : nullptr);
    out = {sub.mixer() != nullptr};
    break;
  case 3:
    sub.setMappingController(variant ? map : nullptr);
    out = {sub.mapping() != nullptr};
    break;
  case 2:
  case 10:
  case 13:
  case 18:
  case 20:
  case 21:
  case 22: {
    Presonus::Surface::MixerPageComponent *object;
    if (id == 18 || id == 21)
      object = new Presonus::Surface::SubAssignPageComponent;
    else if (id == 20 || id == 22)
      object = new Presonus::Surface::GroupsPageComponent(state, deps);
    else
      object = new Presonus::Surface::MixerPageComponent;
    watched = object;
    deletions = 0;
    allocationLive = true;
    if (id == 13 || id == 21 || id == 22)
      delete object;
    else {
      if (id == 18)
        static_cast<Presonus::Surface::SubAssignPageComponent *>(object)
            ->~SubAssignPageComponent();
      else if (id == 20)
        static_cast<Presonus::Surface::GroupsPageComponent *>(object)
            ->~GroupsPageComponent();
      else
        object->~MixerPageComponent();
    }
    out = {deletions, allocationLive};
    watched = nullptr;
    if (!(id == 13 || id == 21 || id == 22))
      ::operator delete(object);
    break;
  }
  case 4: {
    Component first, second, mixes;
    first.addChild(new Component("a"));
    first.addChild(new Component("b"));
    second.addChild(new Component("c"));
    mixes.addChild(new Component("d"));
    access.mainView.channels[0] = &first;
    access.mainView.channels[2] = &mixes;
    access.slaveView.channels[0] = &second;
    access.mainView.slave = variant == 2 ? &access.secondary : nullptr;
    if (variant)
      sub.setMixerComponent(mix);
    sub.buildItemsList();
    out = {sub.items.count()};
    break;
  }
  case 5: {
    Component parent(variant == 3 ? "autofiltergroup" : "filtergroup");
    auto *child = new Component;
    if (variant >= 2)
      parent.addChild(child);
    out = {groups.isAutoGroup(variant ? child : nullptr)};
    if (variant < 2)
      delete child;
    break;
  }
  case 6:
  case 11:
  case 16:
  case 14: {
    const int counts[] = {0, 16, 17, 32, 40, 20};
    const int offsets[] = {0, 0, 0, 4, 20, 2};
    const int requests[] = {-1, 0, 1, 99, -30, std::numeric_limits<int>::max()};
    for (int i = 0; i < counts[variant]; ++i)
      sub.items.add(nullptr);
    sub.listOffset = offsets[variant];
    if (id == 6)
      sub.addListOffset(requests[variant]);
    if (id == 16)
      sub.setListOffset(requests[variant]);
    if (id == 11) {
      out = {sub.getMaxListOffset()};
      break;
    }
    if (id == 14) {
      auto pi = info(variant % 2 ? 101 : 100);
      NumericParam p(pi);
      p.setValue(variant == 0 ? 0 : 1);
      sub.paramChanged(&p, variant == 5 ? 3 : 2);
    }
    out = {sub.listOffset};
    break;
  }
  case 7: {
    auto pi = info();
    NumericParam p0(pi), p1(pi), other(pi);
    p0.setValue(1);
    p1.setValue(variant == 0   ? 0
                : variant == 2 ? -1
                : variant == 3 ? std::numeric_limits<float>::quiet_NaN()
                               : 1);
    other.setValue(1);
    Parameter *ps[] = {&p0, &p1};
    state.selectionParameters = Core::ConstVector<Parameter *>(ps, 2);
    state.listOffset = 4;
    groups.select(variant == 4 ? &other : &p1);
    out = {state.selection, p0.getValue() == 1, p1.getValue() == 1,
           groups.getParameterByTag(1008)->getIntValue()};
    break;
  }
  case 8: {
    Component selected("x"), root;
    root.addChild(new Component("x"));
    if (variant) {
      state.observedGroup = &selected;
      groups.MixerPageComponent::setMixerComponent(mix);
    }
    access.mainView.slave = variant >= 2 ? &access.secondary : nullptr;
    access.slaveView.root = variant == 3 ? nullptr : &root;
    out = {groups.getSelectedSlaveGroup() != nullptr};
    break;
  }
  case 9: {
    Component group;
    ParamInfo ti = info(600);
    ti.type = ParamInfo::kString;
    group.addParameters(&ti, 1, true);
    if (variant == 0)
      group.getParameterByTag(600)->fromString("named");
    ParamInfo ni = info(601, ParamInfo::kStorable);
    group.addParameters(&ni, 1, true);
    const float values[] = {0, 0, .5f, .000001f,
                            std::numeric_limits<float>::quiet_NaN()};
    group.getParameterByTag(601)->setValue(values[variant]);
    out = {groups.isValidGroup(&group)};
    break;
  }
  case 12: {
    auto *first = new Component, *second = new Component;
    auto *g0 = new Component, *g1 = new Component;
    first->addChild(g0);
    second->addChild(g1);
    ParamInfo infos[] = {info(603), info(600)};
    g0->addParameters(infos, 2, true);
    g1->addParameters(infos, 2, true);
    access.containers(first, second);
    struct Spy : Presonus::Surface::GroupsPageComponent {
      using GroupsPageComponent::GroupsPageComponent;
      int changes = 0;
      void paramChanged(Parameter *, int) override { ++changes; }
    } spy(state, deps);
    spy.bindAccess(access);
    spy.MixerPageComponent::setMixerComponent(mix);
    spy.addRemoveObservers(nullptr, variant);
    for (auto *g : {g0, g1})
      for (int tag : {603, 600})
        g->getParameterByTag(tag)->setValue(1);
    out = {spy.changes};
    break;
  }
  case 15: {
    Component selected;
    auto p0 = info(646), p1 = info(685);
    selected.addParameters(&p0, 1, true);
    selected.addParameters(&p1, 1, true);
    groups.observeGroup(variant ? &selected : nullptr);
    if (variant == 2)
      groups.observeGroup(nullptr);
    out = {groups.sourcePortObservedCount()};
    break;
  }
  case 17: {
    struct Controller : ParamObserverBase {
      int edits = 0;
      void paramChanged(Parameter *, int msg) override {
        if (msg == 2)
          ++edits;
      }
    } controller;
    auto pi = info();
    NumericParam p(pi);
    p.setController(&controller);
    if (variant)
      groups.setMappingController(map);
    if (variant == 2)
      mapping.main = &p;
    groups.launchEdit();
    out = {p.getIntValue(), controller.edits};
    break;
  }
  case 19: {
    state.selection = 4;
    auto *container = new Component;
    auto *good = new Component("good"), *bad = new Component("bad");
    auto ti = info(600);
    ti.type = ParamInfo::kString;
    good->addParameters(&ti, 1, true);
    bad->addParameters(&ti, 1, true);
    good->getParameterByTag(600)->fromString("named");
    container->addChild(good);
    container->addChild(bad);
    if (variant >= 2)
      access.containers(container, nullptr);
    else
      delete container;
    if (variant)
      groups.MixerPageComponent::setMixerComponent(mix);
    groups.updateGroups(variant == 3 ? bad : nullptr);
    out = {state.firstGroups.count(), state.secondGroups.count(),
           state.selection};
    break;
  }
  case 23: {
    auto p0 = info(646), p1 = info(685);
    Component observed;
    observed.addParameters(&p0, 1, true);
    observed.addParameters(&p1, 1, true);
    groups.observeGroup(&observed);
    if (variant >= 2)
      groups.MixerPageComponent::setMixerComponent(mix);
    groups.setMixerComponent(variant % 2 ? mix : nullptr);
    out = {groups.mixer() != nullptr, state.selection,
           groups.sourcePortObservedCount()};
    break;
  }
  case 24: {
    state.listOffset = 3;
    state.selection = 4;
    std::vector<ParamInfo> infos(16);
    for (int i = 0; i < 8; ++i) {
      infos[2 * i] = info(100 + 102 * i);
      infos[2 * i + 1] = info(101 + 102 * i);
      infos[2 * i + 1].type = ParamInfo::kString;
    }
    if (variant) {
      groups.addParameters(infos.data(), 16, true);
      pb.visible = &page;
    }
    groups.refreshList();
    out = {state.listOffset, state.selection};
    if (variant) {
      int enabled = 0, active = 0;
      for (int i = 0; i < 8; ++i) {
        auto *p = groups.getParameterByTag(100 + 102 * i);
        enabled += p->isEnabled();
        active += p->getIntValue();
      }
      out.push_back(enabled);
      out.push_back(active);
    }
    break;
  }
  case 25: {
    auto *input = new Component;
    auto *i0 = new Component, *i1 = new Component;
    input->addChild(i0);
    input->addChild(i1);
    auto labelInfo = info(1), assignInfo = info(256);
    i0->addParameters(&labelInfo, 1, true);
    i0->addParameters(&assignInfo, 1, true);
    i1->addParameters(&labelInfo, 1, true);
    i1->addParameters(&assignInfo, 1, true);
    Component subs;
    auto *selected = new Component;
    subs.addChild(selected);
    access.mainView.channels[0] = input;
    access.mainView.channels[4] = &subs;
    access.mainView.selected = selected;
    static auto a0 = info(), n0 = info(), a1 = info(), n1 = info();
    a0.type = n0.type = a1.type = n1.type = ParamInfo::kAlias;
    std::snprintf(a0.name, sizeof a0.name, "assign_slot_01");
    std::snprintf(n0.name, sizeof n0.name, "assign_slot_name_01");
    std::snprintf(a1.name, sizeof a1.name, "assign_slot_02");
    std::snprintf(n1.name, sizeof n1.name, "assign_slot_name_02");
    sub.addParameters(&a0, 1, true);
    sub.addParameters(&n0, 1, true);
    sub.addParameters(&a1, 1, true);
    sub.addParameters(&n1, 1, true);
    sub.setMixerComponent(mix);
    sub.listOffset = variant == 3 ? -1 : variant;
    pb.visible = &page;
    sub.updateParams();
    for (const char *name : {"assign_slot_01", "assign_slot_name_01",
                             "assign_slot_02", "assign_slot_name_02"}) {
      auto *p = Core::Portable::AliasParam::cast(sub.findParameter(name))
                    ->getOriginal();
      out.push_back(p ? p->getTag() : -1);
    }
    // Aliases borrow original parameters; clear before destroying the fixture
    // tree.
    for (const char *name : {"assign_slot_01", "assign_slot_name_01",
                             "assign_slot_02", "assign_slot_name_02"})
      Core::Portable::AliasParam::cast(sub.findParameter(name))
          ->setOriginal(nullptr);
    delete input;
    break;
  }
  case 26: {
    presonus::surface::BorrowedMixerPageAccess rejected;
    bool unknown = false, missing = false, duplicate = false;
    try {
      rejected.mixerRoot(mix);
    } catch (const std::logic_error &) {
      unknown = true;
    }
    presonus::surface::MixerPageView v;
    v.identity = mix;
    rejected.registerView(v);
    try {
      rejected.mixerRoot(mix);
    } catch (const std::logic_error &) {
      missing = true;
    }
    presonus::surface::MixerPageView other;
    other.identity = mix;
    try {
      rejected.registerView(other);
    } catch (const std::logic_error &) {
      duplicate = true;
    }
    if (!unknown || !missing || !duplicate)
      return 7;
    v.root = nullptr;
    if (rejected.mixerRoot(mix) != nullptr)
      return 8;
    bool changed = false, unregistered = false;
    v.identity = &access.secondary;
    try {
      rejected.mixerRoot(mix);
    } catch (const std::logic_error &) {
      changed = true;
    }
    try {
      rejected.mixerRoot(&access.secondary);
    } catch (const std::logic_error &) {
      unregistered = true;
    }
    if (!changed || !unregistered)
      return 9;
    return 0;
  }
  case 27: {
    struct Controller : ParamObserverBase {
      int edits = 0;
      void paramChanged(Parameter *, int msg) override {
        if (msg == 2)
          ++edits;
      }
    } controller;
    auto r0 = info(0), r6 = info(6);
    NumericParam radio(r0), mode(r6);
    radio.setValue(variant == 1 ? 1.f : 0.f);
    mode.setValue(variant == 2 ? 1.f : 0.f);
    radio.setController(&controller);
    mapping.radios[0] = &radio;
    mapping.radios[6] = &mode;
    groups.setMappingController(map);
    auto autoInfo = info(1009);
    groups.addParameters(&autoInfo, 1, true);
    auto *container = new Component;
    auto *selected = new Component("x");
    container->addChild(selected);
    auto positive = info(646), negative = info(647);
    selected->addParameters(&positive, 1, true);
    selected->addParameters(&negative, 1, true);
    selected->getParameterByTag(646)->setValue(1);
    selected->getParameterByTag(647)->setValue(-1);
    access.containers(variant == 2 ? nullptr : container,
                      variant == 2 ? container : nullptr);
    Component *list[] = {selected};
    state.firstGroups = Core::ConstVector<Component *>(list, 1);
    state.selection = variant == 0 ? -1 : 0;
    groups.MixerPageComponent::setMixerComponent(mix);
    groups.doselect();
    int visible = 0;
    if (access.mainSelection.filter) {
      auto &v = access.mainSelection.filter->sourcePortVisibility();
      for (int i = 0; i < v.count(); ++i)
        visible += v.at(i);
    }
    out = {groups.getParameterByTag(1008)->getIntValue(),
           groups.getParameterByTag(1009)->getIntValue(),
           radio.getIntValue(),
           controller.edits,
           access.mainSelection.filter != nullptr,
           access.mainSelection.selectedGroup != nullptr,
           visible};
    groups.observeGroup(nullptr);
    break;
  }
  case 28: {
    Presonus::ChannelGroupFilter filter(2);
    filter.setVisible(1, true);
    int indices[] = {0, 1, 2, -1};
    filter.setVisible(indices[variant], variant != 1);
    auto &v = filter.sourcePortVisibility();
    out = {v.at(0), v.at(1), Core::ConstVector<bool>::getError()};
    break;
  }
  case 29: {
    int counts[] = {0, 1, 5, 6, 39};
    Presonus::ChannelGroupFilter filter(counts[variant]);
    auto &v = filter.sourcePortVisibility();
    int nonzero = 0;
    for (int i = 0; i < v.getCapacity(); ++i)
      nonzero += v.getItems()[i];
    out = {v.count(), v.getCapacity(), nonzero};
    break;
  }
  default:
    return 3;
  }
  for (std::size_t i = 0; i < out.size(); ++i)
    std::cout << (i ? " " : "") << out[i];
  std::cout << '\n';
}
