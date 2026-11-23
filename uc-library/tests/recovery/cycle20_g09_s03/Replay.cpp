#include "presonus/mixer/ReverbComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>

using Receiver = Presonus::Mixer::ReverbComponent;

namespace {
void invokeVirtual(Receiver &receiver) { receiver.tap(); }

struct Probe : Receiver {
  using Receiver::Receiver;
  void tap() override { ++calls; }
  unsigned calls = 0;
};

void checkRoutes(Probe &probe) {
  // Force a qualified direct call and verify the other site dispatches
  // through the dynamic type with a distinct, observable test override.
  probe.Receiver::tap();
  if (probe.calls != 0)
    throw std::runtime_error("qualified call selected test override");
  invokeVirtual(probe);
  if (probe.calls != 1)
    throw std::runtime_error("virtual call bypassed test override");
}

using Snapshot = std::array<unsigned char, sizeof(Receiver)>;

Snapshot receiverBytes(const Receiver &receiver) {
  Snapshot bytes;
  std::memcpy(bytes.data(), &receiver, bytes.size());
  return bytes;
}

bool runCase(bool viaTable, unsigned seed) {
  Receiver receiver{Receiver::SourcePortConstruction{}};
  Probe probe{Receiver::SourcePortConstruction{}};
  checkRoutes(probe);
  const auto snapshot = receiverBytes(receiver);
  const auto *table = receiver.getSelectTypeMap();
  const auto row = table[seed];
  const auto mapped = receiver.mapIDs(seed + 2);
  if (viaTable)
    invokeVirtual(receiver);
  else
    receiver.Receiver::tap();
  const auto *after = receiver.getSelectTypeMap();
  return receiverBytes(receiver) == snapshot && after == table &&
         after[seed].family == row.family && after[seed].index == row.index &&
         after[seed].effectType == row.effectType &&
         after[seed].value == row.value && after[seed].name == row.name &&
         receiver.mapIDs(seed + 2) == mapped;
}

} // namespace

int main() {
  unsigned route, seed;
  while (std::cin >> route >> seed) {
    if (route > 1 || seed > 3)
      return 2;
    std::cout << runCase(route != 0, seed) << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
