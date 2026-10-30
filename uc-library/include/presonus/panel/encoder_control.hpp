#pragma once
#include "presonus/panel/control.hpp"
#include <cstdint>
namespace presonus::panel {
struct EncoderControlAccess;
}
namespace Presonus::Panel {
class EncoderControl : public Control {
public:
  explicit EncoderControl(int);
  ~EncoderControl() override;
  void *castTo(int) override;
  void receiveValue(int) override;

private:
  int highPrecisionThreshold_ = 1;
  std::uint32_t accumulatorBits_ = 0;
  friend struct presonus::panel::EncoderControlAccess;
};
} // namespace Presonus::Panel
namespace presonus::panel {
struct EncoderControlAccess {
  static auto &threshold(Presonus::Panel::EncoderControl &control) {
    return control.highPrecisionThreshold_;
  }
  static auto &accumulator(Presonus::Panel::EncoderControl &control) {
    return control.accumulatorBits_;
  }
};
} // namespace presonus::panel
