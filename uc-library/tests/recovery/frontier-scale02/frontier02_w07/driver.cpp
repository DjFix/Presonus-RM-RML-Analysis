#include "presonus/mixer/AVBCascadeManager.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include <cstdlib>
#include <iostream>
struct Boundary : presonus::mixer::CascadeBoundary {
  void select(Presonus::UC::NetworkItem *, bool) override {}
  bool connectedClientPresent() override { return false; }
  void connectionChanged(bool) override {}
  void updateChannelSelectionSync() override {}
};
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  Boundary b;
  int token;
  std::uint32_t id = std::strtoul(argv[3], nullptr, 0);
  Presonus::UC::NetworkItem item(std::atoi(argv[2]) ? &token : nullptr);
  Presonus::Mixer::AVBCascadeManager manager(b, std::atoi(argv[1]) ? &item
                                                                   : nullptr);
  manager.sourcePortBindComponentIds({{&token, &id}});
  std::cout << manager.getSlaveId() << '\n';
  id ^= 0xffffffffu;
  std::cout << manager.getSlaveId() << '\n';
}
