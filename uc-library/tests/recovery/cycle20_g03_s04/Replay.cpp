#include "presonus/surface/AssignEditPageComponent.hpp"

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <vector>

using namespace Core::Portable;
using Page = Presonus::Surface::AssignEditPageComponent;

struct PageBindings final : presonus::page::Bindings {
  const Presonus::PageComponent *current = nullptr;
  const int *offset = nullptr;
  mutable std::vector<int> trace;

  void *castOwner(void *owner, int classId) const override {
    if (owner != this || classId != 1296843588)
      std::abort();
    return owner;
  }
  const void *currentPage(void *) const override {
    trace.push_back(offset ? 100 + *offset : 100);
    return current;
  }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};

struct Observer final : Component {
  explicit Observer(std::vector<int> &trace) : trace(trace) {}
  void paramChanged(Parameter *p, int message) override {
    if (message == Parameter::kChanged)
      trace.push_back(p->getTag());
  }
  std::vector<int> &trace;
};

ParamInfo info(int tag, const char *name = "", bool alias = false) {
  ParamInfo value;
  value.clear();
  value.tag = tag;
  value.type = alias ? ParamInfo::kAlias : ParamInfo::kFloat;
  value.maxValue = 1;
  std::snprintf(value.name, sizeof value.name, "%s", name);
  return value;
}

int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  bool show = std::atoi(argv[1]);
  bool visible = std::atoi(argv[2]);
  int initial = std::atoi(argv[3]);
  int mode = std::atoi(argv[4]);
  PageBindings bindings;
  Presonus::PageComponent page(&bindings, bindings);
  bindings.current = visible ? &page : nullptr;
  Presonus::MixerClientComponentBase mixer;
  presonus::surface::MixerPageView view;
  presonus::surface::BorrowedMixerPageAccess access;
  Observer observer(bindings.trace);
  Component inputs, returns, buses, old;
  auto *input = new Component;
  auto *bus = new Component;
  inputs.addChild(input);
  buses.addChild(bus);
  view.identity = &mixer;
  view.channels[0] = &inputs;
  view.channels[2] = &returns;
  view.channels[4] = &buses;
  view.slave = nullptr;
  access.registerView(view);
  (void)initial;
  static const ParamInfo inputParams[] = {info(256)};
  static const ParamInfo busParams[] = {info(2), info(411)};
  static const ParamInfo oldInfo[] = {info(44), info(45), info(46)};
  static const ParamInfo params[] = {
      info(10, "slot_chname_01", true), info(11, "slot_assign_01", true),
      info(12, "slot_bus_mode_01", true), info(1000, "assigned")};
  input->addParameters(inputParams, 1);
  bus->addParameters(busParams, 2);
  bus->getParameterByTag(411)->setValue(mode & 1, false);
  old.addParameters(oldInfo, 3);
  view.selected = mode & 2 ? input : nullptr;
  Page target(Page::SourcePortConstruction{});
  target.bindAccess(access);
  target.bindPage(page);
  target.setMixerComponent(&mixer);
  target.addParameters(params, 4);
  auto *visibility = target.getParameterByTag(1000);
  visibility->setValue(!(mode & 1), false);
  visibility->addObserver(&observer);
  for (int i = 0; i < 3; ++i) {
    auto *alias = AliasParam::cast(target.getParameterAt(i));
    alias->setOriginal(old.getParameterAt(i));
    alias->addObserver(&observer);
  }
  target.onShow(show);
  std::cout << visibility->getValue();
  visibility->removeObserver(&observer);
  for (int i = 0; i < 3; ++i) {
    auto *alias = AliasParam::cast(target.getParameterAt(i));
    auto *original = alias->getOriginal();
    std::cout << ' ' << (original ? original->getTag() : -1);
    alias->removeObserver(&observer);
  }
  for (int event : bindings.trace)
    std::cout << ' ' << event;
  std::cout << '\n';
}
