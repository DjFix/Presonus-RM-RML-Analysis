// Canonical state replay. Links the existing CS18 role target; no production
// CPP bodies, entry instrumentation, wrappers or provider substitutes are
// added. Root-level call ordering remains covered by the immutable local
// replay.cpp.
#include "presonus/surface/GroupsPageComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
class Node : public Component {
public:
  using Component::Component;
  Parameter *num(int tag, const char *name, float value = 0.f) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kFloat;
    info->tag = tag;
    std::strncpy(info->name, name, 31);
    info->minValue = -100;
    info->maxValue = 100;
    info->defaultValue = value;
    auto *p = paramList.add(*info, true);
    return p;
  }
  Parameter *text(int tag, const char *name, const char *value) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kString;
    info->tag = tag;
    std::strncpy(info->name, name, 31);
    auto *p = paramList.add(*info, true);
    p->fromString(value, false);
    return p;
  }
};
class Page : public Presonus::Surface::GroupsPageComponent {
public:
  using GroupsPageComponent::GroupsPageComponent;
  void attach(Presonus::MixerClientComponentBase *identity) {
    mixer_ = identity;
  }
  Parameter *add(int tag, const char *name, float value = 0) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kFloat;
    info->tag = tag;
    std::strncpy(info->name, name, 31);
    info->minValue = -100;
    info->maxValue = 100;
    info->defaultValue = value;
    return paramList.add(*info, true);
  }
  void label(int tag) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kString;
    info->tag = tag;
    paramList.add(*info, true);
  }
};
struct Deps : presonus::surface::GroupsPageDependencies {
  void refreshList() override {}
  void doselect() override {}
  void observeGroup(Component *) override {}
};
struct Visibility : presonus::page::Bindings {
  const void *current = nullptr;
  void *castOwner(void *o, int) const override { return o; }
  const void *currentPage(void *) const override { return current; }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
};
struct Mapping : Presonus::IMappingController {
  int getModifiers() const override { return 0; }
  int getRadioValue(int, int) const override { return 0; }
  int getBankScrollingOffset() const override { return 0; }
  bool isDisplayEncoderLocked() const override { return false; }
  bool areFadersLockedToMainMix() const override { return false; }
  void encoderChanged(int) const override {}
  void onSelectedChannelChanged() override {}
  void selectedChannelUpdated() override {}
  void setRadioGroup(int, int, int, bool) override {}
  void onDeviceDisconnected() override {}
  Node params;
  Parameter *getParamByTag(int tag) const override {
    return params.getParameterByTag(tag);
  }
  Parameter *getMainScreenParamByTag(int tag) const override {
    return params.getParameterByTag(tag);
  }
};
int main() {
  int op, tag, msg, own, nameId, selection, offset, match, automatic, mode,
      sourceMode, visible, mapping, member;
  std::uint32_t bits;
  while (std::cin >> op >> tag >> msg >> bits >> own >> nameId >> selection >>
         offset >> match >> automatic >> mode >> sourceMode >> visible >>
         mapping >> member) {
    float value;
    std::memcpy(&value, &bits, 4);
    Node tree("root"), source("source");
    std::vector<Node *> first, second;
    Node *a = nullptr, *b = nullptr;
    if (mode != 0) {
      a = new Node("filtergroup");
      tree.addChild(a);
    }
    if (mode != 0 && mode != 7) {
      b = new Node("autofiltergroup");
      tree.addChild(b);
    }
    auto build = [&](Node *container, std::vector<Node *> &nodes, int n) {
      if (!container)
        return;
      for (int i = 0; i < n; ++i) {
        auto *g = new Node("group");
        container->addChild(g);
        nodes.push_back(g);
        if (!(mode == 4 && i == 0 && container == a))
          g->text(600, "name",
                  ((mode == 3 && i == 1 && container == a) ||
                   (mode == 5 && i == 0 && container == a))
                      ? ""
                      : "occupied");
        if (!(mode == 8 && i == 0))
          g->num(603, "selected", 1);
        g->num(646, "member", 0.25f);
      }
    };
    build(a, first, mode == 1 ? 0 : 12);
    build(b, second, mode == 1 ? 0 : 3);
    const char *names[] = {"copy",
                           "~copy",
                           "",
                           "1234567890123456789012345678901",
                           "~1234567890123456789012345678901",
                           "123456789012345678901234567890123456789"};
    if (sourceMode > 0) {
      if (sourceMode != 7)
        source.text(600, "name", names[(sourceMode - 1) % 6]);
      source.num(603, "selected", 0.5f);
      source.num(646, "member", value);
      if (sourceMode == 8)
        source.num(9999, "extra", .8f);
    }
    presonus::surface::GroupsPageState state;
    Deps deps;
    Page page(state, deps);
    Visibility vis;
    int owner = 0;
    vis.current = visible ? &owner : nullptr;
    Presonus::PageComponent realPage(&owner, vis);
    vis.current = visible ? &realPage : nullptr;
    page.bindPage(realPage);
    presonus::surface::BorrowedMixerPageAccess access;
    presonus::surface::MixerSelectionView viewSelection;
    presonus::surface::MixerPageView view;
    int identity = 0;
    view.identity =
        reinterpret_cast<Presonus::MixerClientComponentBase *>(&identity);
    view.groupTree = &tree;
    view.root = &tree;
    view.slave = static_cast<Presonus::MixerClientComponentBase *>(nullptr);
    view.selectionState = &viewSelection;
    access.registerView(view);
    page.bindAccess(access);
    page.attach(view.identity);
    for (int i = 0; i < 8; ++i) {
      page.add(100 + 102 * i, "button");
      page.label(101 + 102 * i);
    }
    page.add(1008, "enabled");
    page.add(1009, "editmode", 1);
    page.add(8888, "show_auto", automatic ? 1 : 0);
    const char *eventNames[] = {"other", "input_bank", "input_bank_1",
                                "xinput_bank", "show_auto"};
    Node external("foreign");
    Parameter *p = own ? page.add(tag, eventNames[nameId], value)
                       : external.num(tag, eventNames[nameId], value);
    if (!own && match >= 0) {
      Node *g = match < 12 ? first.at(match) : second.at(match - 12);
      p->setController(g);
    }
    if (own)
      p->setController(&page);
    else if (match < 0)
      p->setController(nullptr);
    Parameter *selectionParams[] = {p};
    if (member)
      state.selectionParameters = {selectionParams, 1};
    Mapping map;
    if (mapping) {
      if (mapping != 2)
        map.params.num(6, "mode", 1);
      map.params.num(25, "edit", 0);
      page.setMappingController(&map);
    }
    if (!(op == 4 && mode == 4))
      page.updateGroups(nullptr);
    std::vector<Component *> duplicateFirst, duplicateSecond;
    if (op == 1 && mode == 10) {
      for (auto *g : first)
        duplicateFirst.push_back(g);
      for (auto *g : second)
        duplicateSecond.push_back(g);
      duplicateFirst[1] = duplicateFirst[0];
      duplicateSecond[0] = duplicateFirst[0];
      state.firstGroups = {duplicateFirst.data(),
                           static_cast<int>(duplicateFirst.size())};
      state.secondGroups = {duplicateSecond.data(),
                            static_cast<int>(duplicateSecond.size())};
      page.attach(
          nullptr); // Explicit source-port list views, not tree ownership.
    }
    state.selection = selection;
    state.listOffset = offset;
    if (match >= 0)
      state.observedGroup =
          match < 12 ? first.at(match) : second.at(match - 12);
    Component *selected = match >= 0 ? state.observedGroup : nullptr;
    if (op == 1 && match == -2)
      selected = &source;
    if (op == 1)
      page.selectGroup(selected);
    if (op == 2)
      page.paramChanged(p, msg);
    if (op == 3)
      page.onObserveredParamChange(p, msg);
    if (op == 4)
      page.addGroup(sourceMode ? &source : nullptr);
    // Canonical role archives run without test instrumentation. Zero means
    // unavailable direct-call trace; verifier never treats it as a native
    // trace.
    std::cout << 0;
    if (op == 1)
      std::cout << ' ' << state.selection;
    if (op == 2 && own)
      std::cout << ' ' << page.getParameterByTag(1009)->getValue();
    if (op == 3) {
      for (auto *g : first)
        std::cout << ' '
                  << (g->getParameterByTag(603)
                          ? g->getParameterByTag(603)->getValue()
                          : -99.f);
      for (auto *g : second)
        std::cout << ' '
                  << (g->getParameterByTag(603)
                          ? g->getParameterByTag(603)->getValue()
                          : -99.f);
      if (mapping)
        std::cout << ' '
                  << (map.params.getParameterByTag(6)
                          ? map.params.getParameterByTag(6)->getValue()
                          : -99.f);
    }
    if (op == 4) {
      for (auto *g : first) {
        Core::CString32 text;
        if (auto *n = g->getParameterByTag(600))
          n->toString(text.getBuffer(), 32);
        std::cout << ' ' << std::quoted(text.getBuffer());
        for (int t : {603, 646}) {
          float v = g->getParameterByTag(t)->getValue();
          std::uint32_t out;
          std::memcpy(&out, &v, 4);
          std::cout << ' ' << out;
        }
      }
    }
    std::cout << '\n';
  }
}
