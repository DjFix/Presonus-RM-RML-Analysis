#include "presonus/mixer/ChDelayFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void ChDelayFormatter::print(Data &data) const {
  Core::CString128 text;
  data.value *= 50.f;
  text.appendFormat("%0.1f ms", static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
