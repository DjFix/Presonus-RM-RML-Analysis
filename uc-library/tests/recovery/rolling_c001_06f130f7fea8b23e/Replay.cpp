#include "presonus/avb/AvbComponent.hpp"
#include <iostream>
#include <stdexcept>
using namespace presonus::avb;
class NoServiceCalls final : public ListenerServices {
  [[noreturn]] static void unexpected() {
    throw std::logic_error("unexpected AVB service call");
  }
  Listener *addListener(unsigned long long, unsigned short,
                        unsigned char) override {
    unexpected();
  }
  void removeListener(Listener *) override { unexpected(); }
  void setAudioClockToListener(Listener *) override { unexpected(); }
  void configureStaticTalkerStreams() override { unexpected(); }
  void routeLinkSlotsFromAvb() override { unexpected(); }
  void sendRoutingPacket(const RoutingPacket &) override { unexpected(); }
};
int main() {
  NoServiceCalls services;
  for (int mode : {0, 2, 3}) {
    ListenerState state;
    state.linkMode = mode;
    Presonus::AVB::AvbComponent avb(state, services);
    avb.setName("test");
    avb.handleListenerStateChange(nullptr);
    if (state.linkMode != mode || avb.countChildren() ||
        std::string_view(avb.getName()) != "test")
      return 1;
    std::cout << "unchanged\n";
  }
}
