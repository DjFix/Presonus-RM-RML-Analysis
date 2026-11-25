#include "presonus/uc/ChannelNameFormatter.hpp"
#include "core/public/corestringbuffer.h"
#include <cmath>

namespace Presonus::UC::Format {

ChannelNameFormatter::ChannelNameFormatter() : Core::Formatter("ch_name") {}
ChannelNameFormatter::~ChannelNameFormatter() = default;

void ChannelNameFormatter::print(Core::Formatter::Data &data) const {
  Core::CString128 text;
  if (data.value == 0.f) {
    text = "Off";
  } else {
    // Leave output unchanged outside the validated signed conversion domain.
    if (!std::isfinite(data.value) || data.value < -0x1p31f ||
        data.value >= 0x1p31f)
      return;
    text.appendFormat("Ch %d", static_cast<int>(data.value));
  }
  text.copyTo(data.string, data.size);
}

} // namespace Presonus::UC::Format
