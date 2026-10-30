#include "presonus/mixer_dsp/FilterControllers.hpp"
#include <cstring>
#include <limits>

namespace {
static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
float fromBits(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
std::uint32_t toBits(float value) {
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}
void update(Presonus::Dsp::FilterControllerState &state, float value,
            bool active) {
  state.valueBits = toBits(value);
  const auto previousActive = state.active;
  state.active = active ? 1 : 0;
  state.dirty = 1;
  if (!state.pending)
    state.pending = state.active ? 1 : previousActive;
}
} // namespace

namespace Presonus::Dsp {
float HiPassController::getValue(int index) const {
  return index == 0 ? fromBits(state_.valueBits) : 0.0f;
}
float LoPassController::getValue(int index) const {
  return index == 0 ? fromBits(state_.valueBits) : 0.0f;
}
void HiPassController::setValue(int index, float value) {
  if (index == 0)
    update(state_, value, value > fromBits(1103102476));
}
void LoPassController::setValue(int index, float value) {
  if (index == 0)
    update(state_, value, value < fromBits(0x469c3fff));
}
} // namespace Presonus::Dsp
