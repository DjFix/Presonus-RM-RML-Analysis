#include "../../portable/dice/ProgrammerBuffers.hpp"
#include "presonus/dice/programmer.hpp"
#include <cstdint>

namespace {
void prepareCommand(unsigned char *transmit, unsigned char command, int page) {
  // ARM LSL wraps at32bits; only its low24bits reach the three address bytes.
  // Unsigned shifting preserves negative-page behavior without signed-shift UB.
  const auto address = static_cast<std::uint32_t>(page) << 8;
  transmit[0] = command;
  transmit[1] = static_cast<unsigned char>(address >> 16);
  transmit[2] = static_cast<unsigned char>(address >> 8);
  transmit[3] = static_cast<unsigned char>(address);
}
} // namespace

namespace Presonus::DICE {
std::int32_t Dice3Programmer::dumpPage(int page) {
  auto &buffers = presonus::dice::detail::programmerBuffers();
  prepareCommand(buffers.transmit.data(), 0x03, page);
  return performTransaction(
             {buffers.transmit.data(), 4, buffers.receive.data(), 256}) != 0
             ? -1
             : 0;
}

std::int32_t Dice3Programmer::verifyPage(int page, const unsigned char *data,
                                         int length) {
  if (page >= 8192)
    return -6;
  const auto wait = busyWait(2000);
  if (wait != 0)
    return wait;
  auto &buffers = presonus::dice::detail::programmerBuffers();
  prepareCommand(buffers.transmit.data(), 0x03, page);
  if (performTransaction(
          {buffers.transmit.data(), 4, buffers.receive.data(), 256}) != 0)
    return -9;
  // Original performs unchecked reads after256. That domain is unresolved;
  // source-port safety rejects it after preserving wait/read callback ordering.
  if (length > 256)
    return -9;
  for (int i = 0; i < length; ++i)
    if (buffers.receive[static_cast<unsigned>(i) + 4] != data[i])
      return -9;
  return 0;
}

std::int32_t Dice3Programmer::writePage(int page, const unsigned char *data,
                                        int length) {
  if (page >= 8192)
    return -6;
  const auto wait = busyWait(2000);
  if (wait != 0)
    return wait;
  const auto enable = writeEnable();
  if (enable != 0)
    return enable;
  auto &buffers = presonus::dice::detail::programmerBuffers();
  for (int i = 0; i < 256; ++i)
    buffers.transmit[static_cast<unsigned>(i) + 4] =
        length > i ? data[i] : static_cast<unsigned char>(0xff);
  prepareCommand(buffers.transmit.data(), 0x02, page);
  return performTransaction(
      {buffers.transmit.data(), 260, buffers.receive.data(), 0});
}
} // namespace Presonus::DICE
