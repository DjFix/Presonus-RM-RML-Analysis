#include "presonus/panel/LEDNotifyTask.hpp"
#include "presonus/dice/packet_services.hpp"
bool LEDNotifyTask::idle() {
  const auto now = static_cast<std::uint64_t>(
      (presonus::dice::packetClockRawTicks() / 1000000));
  const auto deadline = start + delay; // ARM adds/adc wraps modulo 2^64.
  // Sign-bit bias implements the original signed high/unsigned low comparison.
  if ((now ^ (std::uint64_t{1} << 63)) <= (deadline ^ (std::uint64_t{1} << 63)))
    return false;
  if (parameter)
    parameter->performEdit();
  return true;
}
