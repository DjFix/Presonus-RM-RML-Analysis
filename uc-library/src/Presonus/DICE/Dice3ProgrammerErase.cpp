#include "../../portable/dice/ProgrammerBuffers.hpp"
#include "presonus/dice/programmer.hpp"
#include <array>

namespace Presonus::DICE {
std::int32_t Dice3Programmer::eraseAll() {
  if (busyWait(2000) != 0)
    return -2;
  if (writeEnable() != 0)
    return -8;
  const unsigned char command = 0xc7;
  auto &buffers = presonus::dice::detail::programmerBuffers();
  // Original ignores this transaction's result, even on ioctl failure.
  performTransaction({&command, 1, buffers.receive.data(), 0});
  return busyWait(20000);
}

std::int32_t Dice3Programmer::eraseSector(int sector) {
  if (sector > 31)
    return -7;
  const auto wait = busyWait(2000);
  if (wait != 0)
    return wait;
  const auto enabled = writeEnable();
  if (enabled != 0)
    return enabled;
  const auto address = static_cast<std::uint32_t>(sector) << 16;
  const std::array<unsigned char, 4> command{
      0xd8, static_cast<unsigned char>(address >> 16),
      static_cast<unsigned char>(address >> 8),
      static_cast<unsigned char>(address)};
  auto &buffers = presonus::dice::detail::programmerBuffers();
  const auto result =
      performTransaction({command.data(), 4, buffers.receive.data(), 0});
  return result != 0 ? result : busyWait(3100);
}
} // namespace Presonus::DICE
