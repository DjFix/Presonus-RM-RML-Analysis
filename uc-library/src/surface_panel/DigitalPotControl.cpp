#include "presonus/surface_panel/DigitalPotControl.hpp"
#include <cstring>
#include <limits>

namespace {
// Defined binary32 conversion matching the observed original libgcc f2iz
// contract. This is app source-port support, not a recovered Core definition.
int legacyParameterInteger(float value) {
  static_assert(sizeof(float) == sizeof(std::uint32_t));
  static_assert(std::numeric_limits<float>::is_iec559 &&
                std::numeric_limits<float>::digits == 24);
  static_assert(sizeof(int) == sizeof(std::int32_t));
  std::uint32_t word;
  std::memcpy(&word, &value, sizeof word);
  const auto exponent = (word >> 23) & 255U;
  const auto fraction = word & 0x7fffffU;
  const bool negative = (word >> 31) != 0;
  if (exponent == 255 && fraction != 0)
    return 0;
  if (exponent < 127)
    return 0;
  if (exponent >= 158)
    return negative ? std::numeric_limits<int>::min()
                    : std::numeric_limits<int>::max();
  std::uint32_t magnitude = 0x800000U | fraction;
  if (exponent >= 150)
    magnitude <<= exponent - 150;
  else
    magnitude >>= 150 - exponent;
  const int integer = static_cast<int>(magnitude);
  return negative ? -integer : integer;
}
} // namespace

namespace Presonus::Panel {
void DigitalPotControl::paramChanged(Core::Portable::Parameter *parameter,
                                     int mode) {
  state_.baseParamChanged(state_.context, parameter, mode);
  if (mode == 3)
    broadcastValue(legacyParameterInteger(parameter->getValue()));
}

void DigitalPotControl::broadcastValue(int value) {
  if (state_.value != value) {
    state_.value = value;
    transmit();
  }
}

void DigitalPotControl::transmit() {
  const std::array<std::uint8_t, 3> prefix{
      0x64, static_cast<std::uint8_t>(state_.tag),
      static_cast<std::uint8_t>(state_.value)};
  if (auto *endpoint = state_.endpoint)
    endpoint->writePrefix(endpoint->context, prefix);
}
} // namespace Presonus::Panel
