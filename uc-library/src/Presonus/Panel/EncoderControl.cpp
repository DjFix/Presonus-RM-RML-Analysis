#include "presonus/panel/encoder_control.hpp"
#include "presonus/panel/key_input_provider.hpp"
#include "presonus/panel/param_edit_handler.hpp"
#include <cstring>
namespace {
std::int32_t signedBits(std::uint32_t raw) {
  std::int32_t value;
  std::memcpy(&value, &raw, sizeof(value));
  return value;
}
} // namespace
namespace Presonus::Panel {
EncoderControl::EncoderControl(int tag) : Control(tag) {}
EncoderControl::~EncoderControl() = default;
void *EncoderControl::castTo(int tag) {
  return tag == 0x456e6343 ? this : Control::castTo(tag);
}
void EncoderControl::receiveValue(int delta) {
  auto *parameter = getParameter();
  if (!parameter || !parameter->isEnabled())
    return;
  if (KeyInputProvider::instance().altKeyPressed()) {
    getParameter()->resetValue(true);
    return;
  }
  const int precision = getParameter()->getPrecision();
  const int threshold = precision <= 99               ? 40
                        : highPrecisionThreshold_ < 1 ? 1
                                                      : highPrecisionThreshold_;
  accumulatorBits_ += static_cast<std::uint32_t>(delta);
  const auto total = signedBits(accumulatorBits_);
  const auto magnitudeBits =
      total < 0 ? 0u - accumulatorBits_ : accumulatorBits_;
  // ARM compares the wrapped absolute-value bits as signed. INT_MIN remains
  // below every positive threshold; no C++ abs overflow or invented saturation.
  if (threshold > signedBits(magnitudeBits))
    return;
  const int steps = total / threshold;
  accumulatorBits_ = 0;
  if (!steps)
    return;
  presonus::panel::ControlAccess::paramEdits().handleParamEdit(getParameter());
  if (steps > 0)
    getParameter()->increment(steps);
  else
    getParameter()->decrement(-steps);
}
} // namespace Presonus::Panel
