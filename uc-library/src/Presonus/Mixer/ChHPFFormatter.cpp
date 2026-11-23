#include "presonus/mixer/ChHPFFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void ChHPFFormatter::print(Data &data) const {
  Core::CString128 text;
  const float scaled = data.value * 10.f;
  const float frequency = scaled - 80.f;
  if (data.value == 0.f)
    text.append("Off");
  else
    text.appendFormat("%1.1f Hz", static_cast<double>(frequency));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
