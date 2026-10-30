#include "presonus/avb/protocol.hpp"
#include "presonus/avb/receive_services.hpp"
#include "presonus/dice/sysex.hpp"

#include <algorithm>
#include <array>
#include <cassert>

namespace Presonus::AVB {
void AvbManagerBase::receive(const DICE::SysexPacket &packet) {
  assert(receiveContext_ != nullptr);
  auto &context = *receiveContext_;
  if (context.processingWord <= 0)
    return;
  if (packet.length > 1) {
    const auto command = packet.bytes[1];
    if (command >= 0x23 && command <= 0x2f &&
        (0x1c3fU & (1U << (command - 0x23U))) != 0) {
      context.command = command;
      context.status = packet.bytes[2];
      return;
    }
  }

  auto decoded = context.initialScratch;
  // Original length-zero unpack reads data[-1]. The extra byte makes that
  // explicitly modeled read valid C++; it does not recover the old packet ABI.
  std::array<unsigned char, 257> paddedSource;
  paddedSource[0] = context.prefixBeforeData;
  std::copy(packet.bytes.begin(), packet.bytes.end(), paddedSource.begin() + 1);
  if (unpackAvbSpiMsg(decoded.data(), paddedSource.data() + 1, packet.length) !=
      0)
    return;
  if (packet.length <= 1)
    return;
  if (packet.bytes[1] == 0x2a) {
    for (auto *listener : context.listeners) {
      if (listener->inspectState().identifierByte == decoded[2]) {
        if (listener->update(decoded[3], decoded[4], decoded[5])) {
          assert(context.notices != nullptr);
          context.notices->listenerChanged(context.noticeIdentity, listener);
        }
        return;
      }
    }
  } else if (packet.bytes[1] == 0x2b) {
    for (auto *talker : context.talkers) {
      if (talker->inspectState().identifierByte == decoded[2]) {
        if (talker->update(decoded[3], decoded[4])) {
          assert(context.notices != nullptr);
          context.notices->talkerChanged(context.noticeIdentity, talker);
        }
        return;
      }
    }
  }
}
} // namespace Presonus::AVB
