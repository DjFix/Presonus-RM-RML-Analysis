#include "presonus/StormMuteGroupComponent.hpp"
#include <cstdlib>
#include <iostream>
struct Services final : presonus::storm_mute_port::Services {
  void refreshSip() override {}
  void activate(unsigned int) override {}
  Core::Portable::Component *connectedClient() override { return nullptr; }
  void muteGroupStored(int) override {}
  bool load(presonus::storm_mute_port::Group &) override { return false; }
};
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int index = static_cast<int>(std::strtol(argv[2], nullptr, 10));
  const char *prefix = std::string(argv[3]) == "<null>" ? nullptr : argv[3];
  Services services;
  presonus::storm_mute_port::State state(services);
  Presonus::StormMuteGroupComponent object(state);
  Presonus::StormMuteGroupComponent::kDefaultName = prefix;
  auto result = object.createDefaultName(index);
  std::cout << result.str();
}
