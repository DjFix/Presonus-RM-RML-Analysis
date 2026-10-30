#include "core/system/coredebug.h"
#include "presonus/dice/packet_logging.hpp"
#include <cstring>

namespace presonus::dice {
namespace {
bool after(std::uint32_t low, std::uint32_t high, std::uint64_t started) {
  const auto startHigh = static_cast<std::uint32_t>(started >> 32);
  return (high ^ 0x80000000u) > (startHigh ^ 0x80000000u) ||
         (high == startHigh && low > static_cast<std::uint32_t>(started));
}
int lowDifference(std::uint32_t value, std::uint64_t started) {
  static_assert(sizeof(int) == sizeof(std::uint32_t));
  const std::uint32_t difference = value - static_cast<std::uint32_t>(started);
  int signedBits;
  std::memcpy(&signedBits, &difference, sizeof(signedBits));
  return signedBits;
}
} // namespace

void logPacket(const unsigned char *bytes,
               const std::array<std::uint32_t, 4> &timestamps,
               std::int64_t started, const void *context,
               PacketCommandName commandName) {
  const auto bits = static_cast<std::uint64_t>(started);
  if (after(timestamps[0], timestamps[1], bits))
    Core::DebugPrintf("post:%d\t", lowDifference(timestamps[0], bits));
  if (after(timestamps[2], timestamps[3], bits))
    Core::DebugPrintf("read:%d\t", lowDifference(timestamps[2], bits));
  for (unsigned index = 0; index < 24; ++index) {
    const auto byte = bytes[index];
    if (index == 1)
      Core::DebugPrintf("%s\t", commandName(context, byte));
    else
      Core::DebugPrintf("%.2X ", static_cast<unsigned>(byte));
    if (byte == 0xf7)
      break;
  }
  Core::DebugPrintf("\n");
}
} // namespace presonus::dice
