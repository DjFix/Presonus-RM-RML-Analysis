#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/surface/AssignEditPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string_view>

using namespace Core::Portable;
namespace {
struct PageBindings final : presonus::page::Bindings {
  void *owner = nullptr;
  const void *visible = nullptr;
  void *castOwner(void *input, int) const override {
    return input == owner ? owner : nullptr;
  }
  const void *currentPage(void *) const override { return visible; }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { return false; }
};
void add(Component &owner, int tag, const char *name, float value) {
  ParamInfo info = PARAM_FLOAT(tag, "", -10, 10, 0, 0, nullptr, nullptr, 0, 0);
  Core::ConstString(name).copyTo(info.name, sizeof(info.name));
  owner.addParameters(&info, 1, true);
  owner.getParameterByTag(tag)->setValue(value);
}
struct AssignPage final : Presonus::Surface::AssignEditPageComponent {
  AssignPage() : AssignEditPageComponent(SourcePortConstruction{}) {}
  Parameter *alias(int tag, const char *name) {
    return paramList.addAlias(tag, name);
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 9)
    return 2;
  const std::string_view command(argv[1]);
  const bool visible = std::atoi(argv[2]);
  const int mixerKind = std::atoi(argv[3]);
  const int selectedKind = std::atoi(argv[4]);
  const int value = std::atoi(argv[5]);
  const int prebound = std::atoi(argv[6]);
  const int msg = std::atoi(argv[7]);
  const std::string_view name(argv[8]);

  Presonus::MixerClientComponentBase mixer, slave;
  Component inputs, returns, buses, slaveInputs;
  auto *input = new Component("input");
  auto *returned = new Component("return");
  auto *remote = new Component("remote");
  auto *bus = new Component("bus");
  auto *empty = new Component("missing-mode");
  inputs.addChild(input);
  returns.addChild(returned);
  slaveInputs.addChild(remote);
  buses.addChild(empty);
  buses.addChild(bus);
  Component old("previous");
  add(old, 80, "old", 1);
  add(*input, 257, "input_assign", 1);
  add(*returned, 257, "return_assign", 2);
  add(*remote, 257, "remote_assign", 3);
  add(*bus, 2, "bus_name", 4);
  if (mixerKind != 4)
    add(*bus, 411, "bus_mode", value);

  Component &other = old;
  Component *selected = selectedKind == 1   ? input
                        : selectedKind == 2 ? returned
                        : selectedKind == 3 ? remote
                        : selectedKind == 4 ? &other
                                            : nullptr;
  presonus::surface::MixerPageView view, slaveView;
  view.identity = &mixer;
  view.channels[0] = mixerKind == 5 ? nullptr : &inputs;
  view.channels[2] = mixerKind == 6 ? nullptr : &returns;
  view.channels[4] = mixerKind == 2 ? nullptr : &buses;
  view.selected = selected;
  view.slave = mixerKind == 3 ? &slave : nullptr;
  slaveView.identity = &slave;
  slaveView.channels[0] = &slaveInputs;
  presonus::surface::BorrowedMixerPageAccess access;
  access.registerView(view);
  access.registerView(slaveView);

  PageBindings bindings;
  int owner;
  bindings.owner = &owner;
  Presonus::PageComponent page(&owner, bindings);
  bindings.visible = visible ? &page : nullptr;
  AssignPage component;
  component.bindAccess(access);
  component.bindPage(page);
  component.setMixerComponent(mixerKind == 0 ? nullptr : &mixer);
  add(component, 1000, "visibility", -1);
  add(component, 1001, "sel_chnum", 0);
  add(component, 1002, "xslot_bus_mode", 0);
  add(component, 1003, "plain", 0);
  auto *assign = AliasParam::cast(component.alias(200, "slot_assign_02"));
  auto *channel = AliasParam::cast(component.alias(201, "slot_chname_02"));
  auto *busMode = AliasParam::cast(component.alias(202, "slot_bus_mode_02"));
  // Non-alias input must fail the native Parameter -> AliasParam downcast.
  add(component, 203, "slot_assign_01", 9);
  if (prebound)
    for (auto *alias : {assign, channel, busMode})
      alias->setOriginal(old.getParameterByTag(80));

  if (command == "visibility")
    component.updateVisibility();
  else if (command == "aliases")
    component.updateAliasTargets();
  else if (command == "changed")
    component.paramChanged(component.findParameter(name.data()), msg);
  else
    return 3;

  const auto identify = [&](AliasParam *alias) {
    auto *parameter = alias->getOriginal();
    if (parameter == old.getParameterByTag(80))
      return 80;
    if (!parameter)
      return 0;
    if (parameter->getTag() == 257)
      return static_cast<int>(parameter->getValue()) + 250;
    return parameter->getTag();
  };
  std::cout << component.getParameterByTag(1000)->getValue() << ' '
            << identify(assign) << ' ' << identify(channel) << ' '
            << identify(busMode) << '\n';
}
