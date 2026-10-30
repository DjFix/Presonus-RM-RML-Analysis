#include "core/system/coredebug.h"
#include "presonus/dice/uart_assembly.hpp"

namespace presonus::dice {
void CclAssemblyCallbacks::noReceiver(unsigned type) {
  Core::DebugPrintf("Warning no Receiver found for packet. Type: %x\n", type);
}
void CclAssemblyCallbacks::packetLog(
    const Presonus::DICE::SysexPacket &packet) {
  sink_.log(
      packet); // Explicit borrowed application log body, not recovered here.
}
void CclAssemblyCallbacks::sourcePortError(AssemblyError error,
                                           unsigned value) {
  Core::DebugPrintf(
      "UART source port rejected unsupported state: error=%u value=%u\n",
      static_cast<unsigned>(error), value);
}
} // namespace presonus::dice
