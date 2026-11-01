#include "presonus/mixer/AVBCascadeManager.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
struct Boundary : presonus::mixer::CascadeBoundary {
  bool present;
  void select(Presonus::UC::NetworkItem *p, bool b) override {
    std::cout << "select " << reinterpret_cast<std::uintptr_t>(p) << ' ' << b
              << '\n';
  }
  bool connectedClientPresent() override {
    std::cout << "get\n";
    return present;
  }
  void connectionChanged(bool b) override {
    std::cout << "changed " << b << '\n';
  }
  void updateChannelSelectionSync() override { std::cout << "sync\n"; }
};
int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  auto n = [](const char *s) { return std::strtoull(s, nullptr, 0); };
  auto item = reinterpret_cast<Presonus::UC::NetworkItem *>(n(argv[3]));
  Boundary b;
  b.present = n(argv[4]) != 0;
  Presonus::Mixer::AVBCascadeManager m(
      b, reinterpret_cast<Presonus::UC::NetworkItem *>(n(argv[2])));
  switch (n(argv[1])) {
  case 1:
    m.connect(item);
    break;
  case 2:
    m.onNetworkShutdown();
    break;
  case 3:
    std::cout << "result " << m.isConnected(item) << '\n';
    break;
  case 4:
    m.onNetworkItemRemoved(item);
    break;
  case 5:
    m.cardConnectionChanged(n(argv[5]) != 0);
    std::cout << "card " << m.sourcePortCardConnected() << '\n';
    break;
  default:
    return 2;
  }
}
