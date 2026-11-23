#include "presonus/mixer/SubDelayFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void SubDelayFormatter::print(Data &data) const {
  Core::CString128 text;
  if (data.value < 50.f)
    text.appendFormat("%0.1f ms", static_cast<double>(data.value));
  else if (data.value < 2147483648.f)
    text.appendFormat("%d ms", static_cast<int>(data.value));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
