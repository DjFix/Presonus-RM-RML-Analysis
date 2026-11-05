#include "core/system/coredebug.h"
#include "core/system/corethread.h"
#include "presonus/dice/codec.hpp"
#include "presonus/noaa/card.hpp"
#include <stdexcept>
namespace Presonus::NOAA {
unsigned char TCard::programSerialReset() {
  if (!state_.expectedSerial)
    throw std::logic_error("TCard serial binding required");
  const auto serial = *state_.expectedSerial;
  unsigned char bytes[] = {0xf0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xf7};
  const auto alternate =
      state_.observedWord14 == 1 || state_.observedWord14 == 2;
  ::pack32(alternate ? generateAlternateMac(serial) : serial, bytes + 2);
  ::pack32(serial, bytes + 7);
  bytes[12] = static_cast<unsigned char>(state_.observedWord30);
  SysexPacket packet(bytes, sizeof(bytes));
  post(packet);
  Core::DebugPrintf("programming serial reset\n", int(state_.observedWord3c),
                    int(state_.observedWord30));
  Core::Threads::CurrentThread::sleep(4000);
  return waitAck(500);
}
} // namespace Presonus::NOAA
