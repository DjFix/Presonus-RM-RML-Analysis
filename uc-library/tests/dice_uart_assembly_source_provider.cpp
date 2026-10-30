#include "presonus/dice/uart_assembly.hpp"
#include <iostream>
#include <stdexcept>
#include <thread>

namespace {
void require(bool value) {
  if (!value)
    throw std::runtime_error("source-provider assertion");
}
class Sink : public presonus::dice::PacketLogSink {
public:
  int calls = 0;
  void log(const Presonus::DICE::SysexPacket &p) override {
    ++calls;
    require(p.length == 3 && p.bytes[0] == 0xf0 && p.bytes[2] == 0xf7);
    require(p.portableMetadata().constructedQuotient >= 0);
  }
};
class Receiver : public Presonus::DICE::ISysexReceiver {
public:
  bool throwing = false;
  int received = 0;
  bool accepts(const Presonus::DICE::SysexPacket &) override {
    if (throwing)
      throw std::runtime_error("intentional callback exception");
    return true;
  }
  void receive(const Presonus::DICE::SysexPacket &) override { ++received; }
};
bool unlockedFromAnotherThread(presonus::dice::UartAssemblyState &s) {
  bool acquired = false;
  std::thread worker([&] {
    acquired = s.lock.tryLock();
    if (acquired)
      s.lock.unlock();
  });
  worker.join();
  return acquired;
}
} // namespace

int main() {
  std::array<unsigned char, 67> seed{};
  Sink sink;
  presonus::dice::CclAssemblyCallbacks callbacks(sink);
  presonus::dice::UartAssemblyState state(seed, 0, 16);
  Presonus::DICE::Dice3Uart uart(state, callbacks);
  unsigned char frames[] = {0xf0, 1, 0xf7, 0xf0, 2, 0xf7};
  uart.assembleSYSEX(frames, 6);
  require(sink.calls == 2 && state.count == 0);
  require(unlockedFromAnotherThread(state));
  Receiver receiver;
  state.receivers.add(&receiver);
  uart.assembleSYSEX(frames, 3);
  require(receiver.received == 1);
  receiver.throwing = true;
  bool caught = false;
  try {
    uart.assembleSYSEX(frames, 3);
  } catch (const std::runtime_error &) {
    caught = true;
  }
  require(caught && state.count == 0 && unlockedFromAnotherThread(state));
  receiver.throwing = false;
  uart.assembleSYSEX(nullptr, 1);
  require(state.error == presonus::dice::AssemblyError::nullInput);
  require(unlockedFromAnotherThread(state));
  state.receivers.at(0) = nullptr;
  uart.assembleSYSEX(frames, 3);
  require(state.error == presonus::dice::AssemblyError::invalidReceiver);
  require(state.span()[64] == 1 && unlockedFromAnotherThread(state));
  std::cout << "PASS real CCL clocks/buffer/vector/lock/debug adapter; "
               "borrowed packet-log continuation; exception cleanup; explicit "
               "null adaptations\n";
}
