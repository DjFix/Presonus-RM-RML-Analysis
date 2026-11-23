#include "presonus/mixer/ChGainFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void ChGainFormatter::print(Data &data) const {
  Core::CString128 text;
  if (data.value <= -84.f)
    text.append("Off");
  else
    text.appendFormat("%1.1f db", static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
