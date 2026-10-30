#pragma once
#include <cstdint>

namespace Presonus::Dsp {
// Independent portable state; not an original process object or ARM layout.
// Original accesses: process+4 value, +0x139 dirty, +0x13a active;
// controller+0x1c pending and +0x28 process pointer.
struct FilterControllerState {
  std::uint32_t valueBits = 0;
  std::uint8_t dirty = 0, active = 0, pending = 0;
};

class HiPassController {
public:
  explicit HiPassController(FilterControllerState &state) : state_(state) {}
  float getValue(int index) const;
  // Original setter return declaration unresolved; state-only verified.
  void setValue(int index, float value);

private:
  FilterControllerState &state_;
};

class LoPassController {
public:
  explicit LoPassController(FilterControllerState &state) : state_(state) {}
  float getValue(int index) const;
  // Original setter return declaration unresolved; state-only verified.
  void setValue(int index, float value);

private:
  FilterControllerState &state_;
};
} // namespace Presonus::Dsp
