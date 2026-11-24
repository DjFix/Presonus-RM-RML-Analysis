#include "presonus/avb/AvbComponent.hpp"
#include <array>
#include <cstdlib>
#include <iostream>

namespace {
using namespace presonus::avb;

class UnusedServices final : public ListenerServices {
public:
  Listener *addListener(unsigned long long, unsigned short,
                        unsigned char) override {
    std::abort();
  }
  void removeListener(Listener *) override { std::abort(); }
  void setAudioClockToListener(Listener *) override { std::abort(); }
  void configureStaticTalkerStreams() override { std::abort(); }
  void routeLinkSlotsFromAvb() override { std::abort(); }
  void sendRoutingPacket(const RoutingPacket &) override { std::abort(); }
};
} // namespace

int main() {
  for (unsigned seed, present; std::cin >> seed >> present;) {
    if (seed > 240 || present > 1)
      return EXIT_FAILURE;
    std::array<Listener, 4> listeners{{
        {static_cast<unsigned char>(seed)},
        {static_cast<unsigned char>(seed + 1)},
        {static_cast<unsigned char>(seed + 2)},
        {static_cast<unsigned char>(seed + 3)},
    }};
    ListenerState state{&listeners[0],
                        &listeners[1],
                        &listeners[2],
                        &listeners[3],
                        static_cast<int>(seed % 3),
                        seed * 11,
                        nullptr};
    const ListenerState before = state;
    UnusedServices services;
    Presonus::AVB::AvbComponent component(state, services);
    alignas(void *) std::array<unsigned char, 64> talkerToken;
    talkerToken.fill(static_cast<unsigned char>(seed));
    const auto tokenBefore = talkerToken;
    auto *talker =
        present
            ? reinterpret_cast<Presonus::AVB::AvbTalker *>(talkerToken.data())
            : nullptr;
    component.handleTalkerStateChange(talker);
    const bool receiverUnchanged =
        state.cascade == before.cascade && state.mixer == before.mixer &&
        state.csInput == before.csInput && state.console == before.console &&
        state.linkMode == before.linkMode &&
        state.consoleSource == before.consoleSource &&
        state.resource == before.resource && listeners[0].index == seed &&
        listeners[1].index == seed + 1 && listeners[2].index == seed + 2 &&
        listeners[3].index == seed + 3;
    std::cout << receiverUnchanged << ' ' << (talkerToken == tokenBefore)
              << '\n';
    if (!receiverUnchanged)
      return EXIT_FAILURE;
  }
  return std::cin.eof() ? EXIT_SUCCESS : EXIT_FAILURE;
}
