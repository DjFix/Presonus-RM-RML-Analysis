#include "core/system/coredebug.h"
#include "presonus/dice/uart_assembly.hpp"
#include <array>
#include <cerrno>
#include <cstring>

// Actual upstream CCL application-template instantiation, not Core recovery.
DEFINE_SINGLETON(Presonus::DICE::Dice3Uart)

namespace Presonus::DICE {
void Dice3Uart::post(SysexPacket &packet) {
  Core::Threads::ScopedLock guard(state_.lock);
  const auto ticks = presonus::dice::packetClockRawTicks() / 1000000;
  const auto bits = static_cast<std::uint64_t>(ticks);
  packet.portableMetadata().trailingWords[0] = static_cast<std::uint32_t>(bits);
  packet.portableMetadata().trailingWords[1] =
      static_cast<std::uint32_t>(bits >> 32);
  const unsigned length = packet.length;
  if (length > 64) {
    // The original first out-of-range write corrupts the saved lock pointer.
    // Reject it explicitly rather than reproducing stack corruption.
    state_.error = presonus::dice::AssemblyError::invalidTransportWriteLength;
    callbacks_.sourcePortError(state_.error, length);
    return;
  }
  std::array<char, 64> bytes{};
  std::memcpy(bytes.data(), packet.bytes.data(), length);
  const int written = write(bytes.data(), static_cast<int>(length));
  if (written != static_cast<int>(length))
    Core::DebugPrintf("**ERR UART write failure.  Wrote %d, expected %d\n",
                      written, static_cast<int>(length));
}

void Dice3Uart::idleRead() {
  Core::Threads::ScopedLock guard(state_.lock);
  std::array<char, 64> bytes{};
  while (state_.span()[64] == 0) {
    const int received = read(bytes.data(), static_cast<int>(bytes.size()));
    if (received < 0) {
      Core::DebugPrintf("DICE: uart error: %d\n", errno);
      return;
    }
    if (received == 0)
      return;
    if (received > static_cast<int>(bytes.size())) {
      // Real POSIX read cannot exceed its request; arbitrary virtual providers
      // are bounded here instead of reading beyond the original stack buffer.
      state_.error = presonus::dice::AssemblyError::invalidTransportReadLength;
      callbacks_.sourcePortError(state_.error, static_cast<unsigned>(received));
      return;
    }
    assembleSYSEX(reinterpret_cast<unsigned char *>(bytes.data()), received);
  }
}

void Dice3Uart::onIdle() { idleRead(); }

void Dice3Uart::release() { state_.span()[64] = 1; }
} // namespace Presonus::DICE
