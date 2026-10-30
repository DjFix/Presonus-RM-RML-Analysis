#include "presonus/dice/uart_assembly.hpp"
#include <algorithm>
#include <array>
#include <climits>
#include <iostream>
#include <stdexcept>
#include <thread>

namespace {
void require(bool value) {
  if (!value)
    throw std::runtime_error("bounds contract failed");
}
unsigned clocks = 0;
struct Callbacks : presonus::dice::AssemblyCallbacks {
  presonus::dice::UartAssemblyState *state;
  unsigned errors = 0, value = 0;
  presonus::dice::AssemblyError last = presonus::dice::AssemblyError::none;
  explicit Callbacks(presonus::dice::UartAssemblyState &state)
      : state(&state) {}
  void noReceiver(unsigned) override {
    throw std::runtime_error("unexpected parser entry");
  }
  void packetLog(const Presonus::DICE::SysexPacket &) override {
    throw std::runtime_error("unexpected packet");
  }
  void sourcePortError(presonus::dice::AssemblyError error,
                       unsigned input) override {
    bool unlocked = false;
    std::thread probe([&] {
      unlocked = state->lock.tryLock();
      if (unlocked)
        state->lock.unlock();
    });
    probe.join();
    require(!unlocked); // Actual CCL mutex remains held at rejection.
    ++errors;
    last = error;
    value = input;
  }
};
struct Port : Presonus::DICE::Dice3Uart {
  using Dice3Uart::Dice3Uart;
  unsigned reads = 0, writes = 0;
  int supplied = 0;
  std::array<char, 64> sent{};
  int read(char *, int size) override {
    require(size == 64);
    ++reads;
    return supplied;
  }
  int write(const char *data, int size) override {
    require(size >= 0 && size <= 64);
    ++writes;
    std::copy_n(data, size, sent.begin());
    return size;
  }
};
} // namespace

extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *, ...) {}
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  ++clocks;
  return -1000001;
}
} // namespace presonus::dice

int main() {
  for (unsigned length : {64u, 65u, 255u}) {
    std::array<unsigned char, 67> seed{};
    seed[1] = 0x91;
    presonus::dice::UartAssemblyState state(seed, 7, 5);
    Callbacks callbacks(state);
    Port port(state, callbacks);
    Presonus::DICE::SysexPacket packet;
    packet.length = static_cast<unsigned char>(length);
    for (unsigned i = 0; i < packet.bytes.size(); ++i)
      packet.bytes[i] = i;
    const auto before = packet.bytes;
    clocks = 0;
    port.post(packet);
    require(clocks == 1 && callbacks.errors == (length > 64 ? 1u : 0u));
    require(port.writes == (length <= 64 ? 1u : 0u) && port.reads == 0);
    require(packet.portableMetadata().trailingWords[0] == 0xffffffffu &&
            packet.portableMetadata().trailingWords[1] == 0xffffffffu);
    require(packet.bytes == before && state.count == 7 &&
            std::equal(seed.begin(), seed.end(), state.span()));
    if (length > 64)
      require(callbacks.last ==
                  presonus::dice::AssemblyError::invalidTransportWriteLength &&
              callbacks.value == length);
    else
      require(std::equal(port.sent.begin(), port.sent.end(),
                         reinterpret_cast<const char *>(before.data())));
  }
  for (int supplied : {0, 65, INT_MAX}) {
    std::array<unsigned char, 67> seed{};
    seed[1] = 0x91;
    presonus::dice::UartAssemblyState state(seed, 7, 5);
    Callbacks callbacks(state);
    Port port(state, callbacks);
    port.supplied = supplied;
    clocks = 0;
    port.idleRead();
    require(port.reads == 1 && port.writes == 0 && clocks == 0);
    require(callbacks.errors == (supplied > 64 ? 1u : 0u));
    require(state.count == 7 &&
            std::equal(seed.begin(), seed.end(), state.span()));
    if (supplied > 64)
      require(callbacks.last ==
                  presonus::dice::AssemblyError::invalidTransportReadLength &&
              callbacks.value == static_cast<unsigned>(supplied));
  }
  std::cout << "PASS 6 defined source-port bounds cases\n";
}
