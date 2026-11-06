#include "presonus/StormMuteGroupComponent.hpp"
#include <cstring>
#include <iostream>
#include <stdexcept>
using namespace Core::Portable;
namespace {
struct Services : presonus::storm_mute_port::Services {
  void refreshSip() override {}
  void activate(unsigned int) override {}
  Component *connectedClient() override { return nullptr; }
  void muteGroupStored(int) override {}
  bool load(presonus::storm_mute_port::Group &) override { return false; }
};
void require(bool condition) {
  if (!condition)
    throw std::runtime_error("shared safe-list composition mismatch");
}
void composition() {
  Services services;
  presonus::storm_mute_port::State state(services);
  Presonus::StormMuteGroupComponent storm(state);
  const Presonus::StormMuteGroupComponent::SafeMuteFilter filter(state);
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.maxValue = 1.f;
  std::strcpy(info.name, "mute");
  NumericParam parameter(info);
  parameter.setValue(1.f);
  require(!filter.shouldLoad(Parameter::kTypeID, "ignored", &parameter));
  require(state.loose.count() == 1 && state.loose[0] == &parameter);
  storm.onMuteChanged(&parameter);
  require(state.loose.count() == 2);
  parameter.setValue(0.f);
  require(filter.shouldSave(Parameter::kTypeID, "wrong", &parameter));
  storm.onMuteChanged(&parameter);
  require(state.loose.count() == 1);
  presonus::mute_group_port::State groupState;
  presonus::storm_mute_port::Group group(groupState);
  groupState.members.add(&parameter);
  state.groups.add(&group);
  storm.groupWasStored(0);
  require(state.loose.isEmpty());
  require(!filter.shouldSave(Parameter::kTypeID, "mute", &parameter));
  filter.shouldLoad(Parameter::kTypeID, nullptr, &parameter);
  require(state.loose.count() == 1);
  state.loose.empty();
  require(!filter.shouldSave(Parameter::kTypeID, nullptr, &parameter));
  state.groups.empty(); // Borrowed group lifetime ends before Storm destructor.
  std::cerr << "shared-state composition passed: filter/load/save, "
               "onMuteChanged, groupWasStored, external clear\n";
}
} // namespace
int main() {
  composition();
  const char *names[] = {"mute",  "",       "Mute",  "muteX",
                         "xmute", "volume", "mute ", ""};
  const int types[] = {Component::kTypeID, Parameter::kTypeID, 0, -1};
  int mode, type, name, object, count;
  unsigned int bits;
  while (std::cin >> mode >> type >> name >> object >> bits >> count) {
    Services services;
    presonus::storm_mute_port::State state(services);
    ParamInfo infos[3]{};
    for (auto &info : infos) {
      info.type = ParamInfo::kFloat;
      info.maxValue = 1.f;
    }
    std::strcpy(infos[0].name, names[name]);
    std::strcpy(infos[1].name, "mute");
    std::strcpy(infos[2].name, "volume");
    NumericParam first(infos[0]), second(infos[1]), third(infos[2]);
    Parameter *parameters[] = {nullptr, &first, &second, &third};
    first.setValue(bits ? 1.f : 0.f);
    for (int i = 0, id; i < count; ++i) {
      std::cin >> id;
      state.loose.add(parameters[id]);
    }
    const Presonus::StormMuteGroupComponent::SafeMuteFilter filter(state);
    require(core_cast<IStorageFilter>(&filter) != nullptr);
    const IStorageFilter &providerInterface = filter;
    const bool result = mode
                            ? providerInterface.shouldSave(types[type], "wrong",
                                                           parameters[object])
                            : providerInterface.shouldLoad(types[type], nullptr,
                                                           parameters[object]);
    std::cout << int(result) << ' ' << state.loose.count();
    for (int i = 0; i < state.loose.count(); ++i) {
      int id = 0;
      while (parameters[id] != state.loose[i])
        ++id;
      std::cout << ' ' << id;
    }
    std::cout << '\n';
  }
}
