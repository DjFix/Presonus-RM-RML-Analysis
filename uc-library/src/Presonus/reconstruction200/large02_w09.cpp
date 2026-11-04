#include "presonus/reconstruction200/large02_w09.hpp"
#include <cstdint>
#include <cstring>
namespace Presonus {
VUMeterControl::VUMeterControl(const Core::TRect<int> &size)
    : PotControl(size), timer_(0.04f) {
  thresholds_.resize(0);
  timer_.beginAction(-1.f);
  options &= ~4;
}
// Actual member destruction runs timer, threshold vector, then PotControl
// bitmap references and CCL Control cleanup. Native D0 additionally calls
// operator delete.
VUMeterControl::~VUMeterControl() = default;

void VUMeterControl::changeFrames() {
  const int count = thresholds_.count();
  if (!count) {
    PotControl::changeFrames();
    return;
  }
  auto *parameter = getParameter();
  if (!parameter) {
    setFrame(0);
    return;
  }
  const float value = parameter->getNormalized();
  int frame = 0;
  if (options & 0x400000) {
    for (int i = count - 2; i >= 0; --i) {
      if (value < thresholds_[i])
        break;
      ++frame;
    }
  } else {
    while (frame < count - 1 && !(value < thresholds_[frame]))
      ++frame;
  }
  setFrame(frame);
}

void VUMeterControl::setFrame(int frame) {
  // ARM SUB/RSB preserve low 32-bit arithmetic; avoid signed host overflow.
  if (options & 0x400000) {
    const std::uint32_t bits = static_cast<std::uint32_t>(frameCount_) - 1U -
                               static_cast<std::uint32_t>(frame);
    static_assert(sizeof(frame) == sizeof(bits));
    std::memcpy(&frame, &bits, sizeof(frame));
  }
  if (frame != previousValue_)
    dirty_ = true;
  previousValue_ = frame;
}
} // namespace Presonus
