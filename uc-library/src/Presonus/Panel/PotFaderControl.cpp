#include "presonus/panel/param_edit_handler.hpp"
#include "presonus/panel/pot_fader_control.hpp"
#include <cstring>
namespace {
// Exact signed32 -> binary32 RNE -> multiply by 2^-10. This is an independent
// app conversion, not a Core implementation. Integer arithmetic avoids host
// rounding-mode dependence and handles INT_MIN without signed overflow.
std::uint32_t normalizedBits(int input) {
  static_assert(sizeof(int) == sizeof(std::uint32_t));
  const std::uint32_t raw = static_cast<std::uint32_t>(input);
  const bool negative = input < 0;
  const std::uint32_t magnitude = negative ? 0u - raw : raw;
  if (!magnitude)
    return 0;
  unsigned exponent = 0;
  for (auto value = magnitude; value >>= 1;)
    ++exponent;
  std::uint32_t significant;
  if (exponent <= 23) {
    significant = magnitude << (23 - exponent);
  } else {
    const unsigned shift = exponent - 23;
    significant = magnitude >> shift;
    const std::uint32_t remainder = magnitude & ((1u << shift) - 1u);
    const std::uint32_t halfway = 1u << (shift - 1);
    if (remainder > halfway || (remainder == halfway && (significant & 1u)))
      ++significant;
    if (significant == (1u << 24)) {
      significant >>= 1;
      ++exponent;
    }
  }
  return (negative ? 0x80000000u : 0u) | ((exponent + 117u) << 23) |
         (significant & 0x7fffffu);
}
} // namespace
namespace Presonus::Panel {
PotControl::PotControl(int tag) : Control(tag) {}
PotControl::~PotControl() = default;
void *PotControl::castTo(int type) {
  return type == 0x506f7443 || type == 0x4374726c ? this : nullptr;
}
void PotControl::broadcastValue(int) {}
void PotControl::receiveValue(int value) {
  if (auto *p = getParameter())
    presonus::panel_binding::potFaderParameterCommand(*p, 0,
                                                      normalizedBits(value));
}
FaderControl::FaderControl(int tag) : PotControl(tag) {}
FaderControl::~FaderControl() = default;
void *FaderControl::castTo(int type) {
  return type == 0x46616443 || type == 0x506f7443 || type == 0x4374726c
             ? this
             : nullptr;
}
void FaderControl::broadcastValue(int) {}
void FaderControl::receiveValue(int value) {
  // Preserve the unconditional edit-service call, then reload the parameter.
  presonus::panel::ControlAccess::paramEdits().handleParamEdit(getParameter());
  if (auto *p = getParameter())
    presonus::panel_binding::potFaderParameterCommand(*p, 0,
                                                      normalizedBits(value));
}
void FaderControl::handleTouch(bool touched) {
  if (auto *p = getParameter())
    presonus::panel_binding::potFaderParameterCommand(*p, touched ? 1 : 2);
}
} // namespace Presonus::Panel
