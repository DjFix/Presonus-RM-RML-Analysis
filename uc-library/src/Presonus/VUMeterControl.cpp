#include "presonus/VUMeterControl.hpp"
#include "core/public/corestringtraits.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
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
void VUMeterControl::setAttributes(
    const Core::Portable::Attributes &attributes) {
  PotControl::setAttributes(attributes);
  const Core::EnumInfo meterOptions[] = {{"reverse", 0x400000}, {nullptr, 0}};
  options |=
      Core::Portable::ViewAttributes::getOptions(attributes, meterOptions);
  const char *table = attributes.getString("dbtable");
  if (!table)
    return;
  thresholds_.resize(0);
  // Actual CCL tokenizer owns the full string. The native unused 127-byte copy
  // is intentionally omitted; global strtok concurrency is not reproduced.
  Core::CStringTokenizer tokenizer(table, ",");
  while (const char *token = tokenizer.next()) {
    if (!*token)
      break;
    float decibels = 0.f;
    std::sscanf(token, "%f", &decibels);
    std::uint32_t bits = 0x3f7fffff;
    float threshold;
    std::memcpy(&threshold, &bits, sizeof(threshold));
    if (!(decibels < -144.f))
      threshold = 1.f - ::powf(10.f, decibels * 0.05f);
    thresholds_.add(threshold);
  }
}

void VUMeterControl::onIdle() {
  Core::Portable::Control::onIdle();
  if (!timer_.isLongEnoughYet())
    return;
  if (dirty_) {
    invalidate();
    dirty_ = false;
  }
  timer_.reset();
  timer_.beginAction(-1.f);
}
} // namespace Presonus
