#include "core/system/coredebug.h"
#include "presonus/noaa/spi_packets.hpp"

namespace Presonus::NOAA {
void TCardSPI::registerReceiver(ISysexReceiver *receiver) {
  Core::Threads::ScopedLock guard(state_.lock);
  state_.receivers.add(receiver);
}

void TCardSPI::unRegisterReceiver(ISysexReceiver *receiver) {
  Core::Threads::ScopedLock guard(state_.lock);
  state_.receivers.remove(receiver);
}

void TCardSPI::release() { state_.disabled = 1; }

void TCardSPI::assembleSYSEX(unsigned char *data, int length) {
  Core::Threads::ScopedLock guard(state_.lock);
  if (state_.disabled != 0 || length <= 0)
    return;
  auto fail = [&](presonus::noaa::SpiPacketError error, unsigned value) {
    state_.error = error;
    state_.disabled = 1;
    Core::DebugPrintf("NOAA SPI source-port bounds error %u at %u\n",
                      static_cast<unsigned>(error), value);
  };
  if (!data) {
    fail(presonus::noaa::SpiPacketError::nullInput,
         static_cast<unsigned>(length));
    return;
  }
  for (int index = 0; index < length; ++index) {
    const auto byte = data[index];
    if (byte == 0xf0) {
      state_.span()[0] = byte;
      state_.count = 1;
      continue;
    }
    if (byte == 0xff || byte == 0xf8)
      continue;
    const auto oldCount = state_.count;
    if (oldCount >= 256) {
      // Original writes into disabled/storage fields above the 256-byte span.
      // This fail-closed branch is a defined adaptation, no ARM equivalence.
      ++state_.rejectedUnsafeWrites;
      fail(presonus::noaa::SpiPacketError::receiveOverflow, oldCount);
      return;
    }
    state_.span()[oldCount] = byte;
    state_.count = oldCount + 1;
    if (byte != 0xf7)
      continue;
    // ARM keeps a32-bit receive count but truncates packet length to8bits.
    SysexPacket packet(state_.span(), static_cast<unsigned char>(state_.count));
    state_.count = 0;
    const auto tick = presonus::dice::packetClockRawTicks() / 1000000;
    const auto bits = static_cast<std::uint64_t>(tick);
    packet.portableMetadata().trailingWords[2] =
        static_cast<std::uint32_t>(bits);
    packet.portableMetadata().trailingWords[3] =
        static_cast<std::uint32_t>(bits >> 32);
    const int count = state_.receivers.count();
    auto *const receivers = state_.receivers.getItems();
    if (count < 0 || count > state_.receivers.getCapacity() ||
        (count != 0 && !receivers)) {
      fail(presonus::noaa::SpiPacketError::invalidReceiverCount,
           static_cast<unsigned>(count));
      return;
    }
    bool accepted = false;
    for (int receiverIndex = 0; receiverIndex < count; ++receiverIndex) {
      auto *const receiver = receivers[receiverIndex];
      if (!receiver) {
        fail(presonus::noaa::SpiPacketError::invalidReceiver, receiverIndex);
        return;
      }
      if (receiver->accepts(packet)) {
        receiver->receive(packet);
        accepted = true;
        break;
      }
      if (receiverIndex + 1 < count &&
          state_.receivers.getItems() != receivers) {
        fail(presonus::noaa::SpiPacketError::receiverStorageChanged,
             receiverIndex);
        return;
      }
    }
    if (!accepted) {
      Core::DebugPrintf("Warning no Receiver found for packet");
      packet.log();
    }
  }
}
} // namespace Presonus::NOAA
