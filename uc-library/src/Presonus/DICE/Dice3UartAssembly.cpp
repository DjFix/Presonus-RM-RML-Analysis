#include "presonus/dice/uart_assembly.hpp"

namespace Presonus::DICE {
void Dice3Uart::assembleSYSEX(unsigned char *data, int length) {
  Core::Threads::ScopedLock guard(state_.lock);
  // Original checks disabled exactly once, after locking, even for empty input.
  if (state_.span()[64] != 0 || length <= 0)
    return;
  if (!data) {
    state_.error = presonus::dice::AssemblyError::nullInput;
    callbacks_.sourcePortError(state_.error, static_cast<unsigned>(length));
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
    if (oldCount >= 67) {
      // Original would now overwrite the mutex and then possibly container
      // state. This deliberate defined source-port adaptation is NOT an
      // equivalence claim for corrupted Core objects/pointers or8-bit wrap.
      state_.error = presonus::dice::AssemblyError::mutexOverlap;
      ++state_.rejectedUnsafeWrites;
      state_.count = 0;
      state_.span()[64] = 1;
      callbacks_.sourcePortError(state_.error, oldCount);
      return;
    }
    state_.span()[oldCount] = byte;
    state_.count = static_cast<unsigned char>(oldCount + 1);
    if (byte != 0xf7)
      continue;
    // Existing constructor supplies both original raw-clock/division stages.
    SysexPacket packet(state_.span(), state_.count);
    state_.count = 0; // Must happen BEFORE the third raw clock call.
    const auto ticks = presonus::dice::packetClockRawTicks() / 1000000;
    const auto bits = static_cast<std::uint64_t>(ticks);
    packet.portableMetadata().trailingWords[2] =
        static_cast<std::uint32_t>(bits);
    packet.portableMetadata().trailingWords[3] =
        static_cast<std::uint32_t>(bits >> 32);
    // Match the captured original pointer/count pair; do not copy the list.
    const int count = state_.receivers.count();
    auto *const receivers = state_.receivers.getItems();
    if (count < 0 || count > state_.receivers.getCapacity() ||
        (count != 0 && !receivers)) {
      state_.error = presonus::dice::AssemblyError::invalidReceiverCount;
      state_.span()[64] = 1;
      callbacks_.sourcePortError(state_.error, static_cast<unsigned>(count));
      return;
    }
    bool accepted = false;
    for (int receiverIndex = 0; receiverIndex < count; ++receiverIndex) {
      auto *const receiver = receivers[receiverIndex];
      if (!receiver) {
        state_.error = presonus::dice::AssemblyError::invalidReceiver;
        state_.span()[64] = 1;
        callbacks_.sourcePortError(state_.error, receiverIndex);
        return;
      }
      if (receiver->accepts(packet)) {
        receiver->receive(
            packet); // Reuse saved receiver, even if its slot changed.
        accepted = true;
        break;
      }
      if (receiverIndex + 1 < count &&
          state_.receivers.getItems() != receivers) {
        state_.error = presonus::dice::AssemblyError::receiverStorageChanged;
        state_.span()[64] = 1;
        callbacks_.sourcePortError(state_.error, receiverIndex);
        return;
      }
    }
    if (!accepted) {
      callbacks_.noReceiver(state_.span()[1]);
      callbacks_.packetLog(packet);
    }
  }
}
} // namespace Presonus::DICE
