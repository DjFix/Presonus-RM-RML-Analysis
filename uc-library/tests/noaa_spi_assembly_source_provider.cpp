#include "presonus/noaa/spi_packets.hpp"
#include <iostream>
#include <stdexcept>
#include <thread>

namespace {
void require(bool value) {
  if (!value)
    throw std::runtime_error("NOAA SPI actual-provider assertion");
}
bool unlocked(presonus::noaa::SpiPacketState &state) {
  bool acquired = false;
  std::thread worker([&] {
    acquired = state.lock.tryLock();
    if (acquired)
      state.lock.unlock();
  });
  worker.join();
  return acquired;
}
class Receiver : public Presonus::NOAA::ISysexReceiver {
public:
  bool throwing = false;
  unsigned received = 0;
  bool accepts(const Presonus::NOAA::SysexPacket &) override {
    if (throwing)
      throw std::runtime_error("intentional receiver exception");
    return true;
  }
  void receive(const Presonus::NOAA::SysexPacket &packet) override {
    ++received;
    require(packet.length == 3 && packet.bytes[0] == 0xf0 &&
            packet.bytes[2] == 0xf7);
  }
};
} // namespace

int main() {
  std::array<unsigned char, 256> seed{};
  presonus::noaa::SpiPacketState state(seed, 0, 0, 2);
  Presonus::NOAA::TCardSPI spi(state);
  unsigned char frame[] = {0xf0, 1, 0xf7};
  spi.assembleSYSEX(frame, 3); // Real NOAA log + Core debug, no wrappers.
  require(state.count == 0 && unlocked(state));
  Receiver receiver;
  spi.registerReceiver(&receiver);
  spi.assembleSYSEX(frame, 3);
  require(receiver.received == 1 && state.count == 0 && unlocked(state));
  receiver.throwing = true;
  bool caught = false;
  try {
    spi.assembleSYSEX(frame, 3);
  } catch (const std::runtime_error &) {
    caught = true;
  }
  require(caught && state.count == 0 && unlocked(state));
  receiver.throwing = false;
  spi.unRegisterReceiver(&receiver);
  require(state.receivers.count() == 0);
  // Deliberate adaptations below have no original ARM-equivalence claim.
  spi.assembleSYSEX(nullptr, 1);
  require(state.disabled == 1 &&
          state.error == presonus::noaa::SpiPacketError::nullInput &&
          unlocked(state));
  for (auto count : {256u, 0xffffffffu}) {
    presonus::noaa::SpiPacketState bounds(seed, count, 0, 0);
    Presonus::NOAA::TCardSPI bounded(bounds);
    unsigned char byte = 1;
    bounded.assembleSYSEX(&byte, 1);
    require(bounds.count == count && bounds.disabled == 1 &&
            bounds.rejectedUnsafeWrites == 1 &&
            bounds.error == presonus::noaa::SpiPacketError::receiveOverflow &&
            unlocked(bounds));
  }
  presonus::noaa::SpiPacketState nullState(seed, 0, 0, 1);
  Presonus::NOAA::TCardSPI nullSpi(nullState);
  nullSpi.registerReceiver(nullptr);
  nullSpi.assembleSYSEX(frame, 3);
  require(nullState.disabled == 1 &&
          nullState.error == presonus::noaa::SpiPacketError::invalidReceiver &&
          unlocked(nullState));
  std::cout
      << "PASS unwrapped NOAA parser real CCL clock/log/buffer/vector/lock, "
         "callback exception cleanup;4 defined adaptation cases\n";
}
