#include "presonus/avb/AvbComponent.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
using namespace presonus::avb;
class Capture final : public ListenerServices {
public:
  std::array<Listener, 256> pool{};
  unsigned next{40};
  Capture() {
    for (unsigned i = 0; i < pool.size(); ++i)
      pool[i].index = static_cast<std::uint8_t>(i);
  }
  Listener *addListener(unsigned long long id, unsigned short start,
                        unsigned char count) override {
    auto n = next++;
    std::cout << "add " << std::uint32_t(id) << ' ' << std::uint32_t(id >> 32)
              << ' ' << start << ' ' << unsigned(count) << ' ' << n << '\n';
    return &pool[n];
  }
  void removeListener(Listener *p) override {
    std::cout << "remove " << unsigned(p->index) << '\n';
  }
  void setAudioClockToListener(Listener *p) override {
    std::cout << "clock " << unsigned(p->index) << '\n';
  }
  void configureStaticTalkerStreams() override {
    std::cout << "configureStaticTalkerStreams\n";
  }
  void routeLinkSlotsFromAvb() override { std::cout << "routeLink\n"; }
  void sendRoutingPacket(const RoutingPacket &p) override {
    std::cout << "packet";
    for (unsigned i = 0; i < p.words[1] / 4 - 1; ++i)
      std::cout << ' ' << p.words[i];
    std::cout << ' ' << p.enabled << '\n';
  }
};
int main() {
  int target, type, clock, mode, disable, old, link;
  unsigned long long id;
  std::uint32_t source;
  unsigned caseNumber = 0;
  while (std::cin >> target >> type >> id >> clock >> mode >> disable >> old >>
         link >> source) {
    std::cout << "CASE " << caseNumber++ << '\n';
    Capture cap;
    ListenerState state{old ? &cap.pool[10] : nullptr,
                        old ? &cap.pool[11] : nullptr,
                        old ? &cap.pool[12] : nullptr,
                        old ? &cap.pool[13] : nullptr,
                        link,
                        source};
    Presonus::AVB::AvbComponent component(state, cap);
    long long signedId;
    static_assert(sizeof(id) == sizeof(signedId));
    std::memcpy(&signedId, &id, sizeof(id));
    switch (target) {
    case 1:
      component.addListener(
          static_cast<Presonus::AVB::AvbComponent::ListenerType>(type),
          signedId, clock, mode, disable);
      break;
    case 2:
      component.addCSInputListener(signedId, clock);
      break;
    case 3:
      component.addMixerInputListener(signedId, clock);
      break;
    case 4:
      component.addCascadeListener(signedId, clock);
      break;
    case 5:
      component.addConsoleBusListener(signedId, clock, mode, disable);
      break;
    default:
      return 2;
    }
    std::cout << "state";
    for (auto p : {state.cascade, state.mixer, state.csInput, state.console})
      std::cout << ' ' << (p ? unsigned(p->index) : 0);
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
