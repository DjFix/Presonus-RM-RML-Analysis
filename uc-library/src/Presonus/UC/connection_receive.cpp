#include "presonus/uc/connection_receive.hpp"

namespace presonus::uc {
struct ReceiveLockBridge {
  ConnectionReceiveState &state;
  void lock() { state.lock(state.context); }
  void unlock() { state.unlock(state.context); }
};
} // namespace presonus::uc
namespace Presonus::UC {
bool Connection::readEvents() {
  auto &state = *state_.receive;
  unsigned waits = 0;
  for (;;) {
    if (!state.readable(state.context, 1))
      return true;
    int available;
    if (!state.pending) {
      available = state.available(state.context);
      if (available < 0)
        return false;
      if (available <= 5)
        return true;
      state.read(state.context,
                 static_cast<unsigned char *>(state.buffer->getAddress()),
                 6); // Original ignores result.
      const auto *header =
          static_cast<unsigned char *>(state.buffer->getAddress());
      state.magicBits = (std::uint32_t(header[0]) << 8) | header[1];
      state.kindBits =
          static_cast<unsigned short>(header[2] | (unsigned(header[3]) << 8));
      state.length =
          static_cast<unsigned short>(header[4] | (unsigned(header[5]) << 8));
      if (state.magicBits != 0x5543u || state.length > 16384)
        return false;
      state.pending = 1;
    }
    available = state.available(state.context);
    if (int(state.length) > available) {
      if (++waits <= 9)
        continue;
      return true;
    }
    const int transferred = state.read(
        state.context, static_cast<unsigned char *>(state.buffer->getAddress()),
        state.length);
    state.pending = 0;
    if (state.kindBits == 0x100u) {
      auto *item =
          state.factory(state.context)
              .read(reinterpret_cast<const char *>(static_cast<unsigned char *>(
                        state.buffer->getAddress())),
                    state.length);
      if (item) {
        Event &event = item->getData();
        state.receivedBytes +=
            static_cast<std::uint64_t>(static_cast<std::int64_t>(transferred));
        ++state.receivedEvents;
        if (state.observerCount != 0) {
          presonus::uc::ReceiveLockBridge lock{state};
          Core::Threads::TScopedLock<presonus::uc::ReceiveLockBridge> guard(
              lock);
          const int initialCount = state.observerCount;
          // Well-formed callback domain: live entries remain available through
          // the snapshotted initial count. Invalid/shrinking registry fallback
          // pointers and original ARM exception unwinding remain unverified.
          for (int i = 0; i < initialCount; ++i) {
            const auto &observer = state.observers[i];
            observer.received(observer.context, state.connectionIndex, event,
                              transferred, state.connectionName);
          }
        }
        state.append(state.context, item);
      }
    }
    waits = 0;
  }
}
} // namespace Presonus::UC
