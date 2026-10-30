#include "core/system/coredebug.h"
#include "presonus/dice/uart_assembly.hpp"
#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value) {
  if (!value)
    throw std::runtime_error("default real-service contract");
}
struct Services : presonus::panel::UartServices {
  unsigned writes = 0;
  std::array<unsigned char, 64> bytes{};
  int writeFile(int descriptor, const void *data, std::uint32_t size) override {
    require(descriptor == -1 && size == 3);
    ++writes;
    std::copy_n(static_cast<const unsigned char *>(data), size, bytes.begin());
    return size;
  }
  int openFile(const char *, int) override { std::abort(); }
  int closeFile(int) override { std::abort(); }
  int readFile(int, void *, std::uint32_t) override { std::abort(); }
  int exclusive(int, unsigned long) override { std::abort(); }
  int getAttributes(int, termios &) override { std::abort(); }
  void makeRaw(termios &) override { std::abort(); }
  int setSpeed(termios &, speed_t) override { std::abort(); }
  int setAttributes(int, int, const termios &) override { std::abort(); }
  int setFlags(int, int, int) override { std::abort(); }
  void printError(const char *) override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
};
} // namespace

extern "C" int __wrap_open(const char *, int, ...) { std::abort(); }
extern "C" int __wrap_close(int) { std::abort(); }

int main() {
  // Initialize the real SDK debug provider before its singleton registry;
  // registered objects then remain able to log during exit cleanup.
  Core::DebugPrintf("DICE owned lifetime source-provider start\n");
  Services services;
  {
    Presonus::DICE::Dice3Uart port;
    auto &state = presonus::dice::UartLifetimeAccess::state(port);
    require(presonus::dice::UartLifetimeAccess::ownsState(port));
    require(state.count == 0 && state.span()[64] == 0 &&
            state.receivers.count() == 0 &&
            state.receivers.getCapacity() == 0 &&
            state.receivers.getDelta() == 5);
    require(presonus::panel::UartCommAccess::descriptor(port) == -1 &&
            presonus::dice::UartLifetimeAccess::gate(port) == 0xffffffffu);
    unsigned char frame[] = {0xf0, 1, 0xf7};
    // No receivers: actual owned CclAssemblyCallbacks -> CclPacketLogSink ->
    // recovered packet log -> genuine CCL clock/debug provider.
    port.assembleSYSEX(frame, 3);
    require(state.count == 0 &&
            state.error == presonus::dice::AssemblyError::none);
    presonus::panel::UartCommAccess::services(port, services);
    Presonus::DICE::SysexPacket packet(frame, 3);
    const auto before = presonus::dice::packetClockRawTicks() / 1000000;
    port.post(packet);
    const auto after = presonus::dice::packetClockRawTicks() / 1000000;
    const auto &words = packet.portableMetadata().trailingWords;
    const auto timestamp =
        static_cast<std::int64_t>((std::uint64_t(words[1]) << 32) | words[0]);
    require(timestamp >= before && timestamp <= after && services.writes == 1 &&
            std::equal(frame, frame + 3, services.bytes.begin()));
  }
  auto &one = Presonus::DICE::Dice3Uart::instance();
  auto &two = Presonus::DICE::Dice3Uart::instance();
  require(&one == &two && presonus::dice::UartLifetimeAccess::ownsState(one));
  require(presonus::panel::UartCommAccess::descriptor(one) == -1);
  std::cout << "PASS actual CCL singleton/default owned state/logging/clock "
               "and mocked transport; no device opens\n";
  // Actual SDK DeletableList owns this registered singleton until exit.
}
