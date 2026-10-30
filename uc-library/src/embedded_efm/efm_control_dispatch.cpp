#include "efm_control_dispatch.hpp"

namespace presonus::analysis::efm_fader_control_dispatch {
bool initialiseIndexedState(std::uint8_t *ram, std::size_t capacity) {
  if (!ram || capacity < 0x3c9)
    return false;
  ram[0x3c8] = 0;
  const unsigned first = ram[0x3a4];
  for (unsigned i = first; i < 4; ++i) {
    auto *state = ram + 0x1d8 + 0x102 + i * 40;
    state[0] = state[1] = 0;
    state[2] = static_cast<std::uint8_t>(i);
  }
  return true;
}

bool dispatchControlPacket(std::uint8_t *ram, std::size_t capacity,
                           ControlBoundary &boundary) {
  if (!ram || capacity < 0x1d5)
    return false;
  const unsigned command = ram[0x145] & 0x7f;
  switch (command) {
  case 0x20:
  case 0x21:
  case 0x22:
  case 0x23:
  case 0x25:
  case 0x28:
  case 0x29:
  case 0x2a:
    return false; // Other isolated ports own these handlers.
  default:
    break;
  }
  const unsigned destination = ram[0x144] >> 4;
  if (destination != ram[0x1d4] && destination != 15)
    return true;
  switch (command) {
  case 0x11:
    if (capacity < 0x3c9)
      return false;
    boundary.call(ControlEntry::Entry16bc, 0x1d8, 0);
    initialiseIndexedState(ram, capacity);
    boundary.call(ControlEntry::Entry1fa8, 0x1d8, 4);
    return true;
  case 0x24:
    ram[0x1ce] = 1;
    return true;
  case 0x26:
    if (capacity < 0x379)
      return false;
    ram[0x378] = 1;
    return true;
  default:
    return true;
  }
}
} // namespace presonus::analysis::efm_fader_control_dispatch
