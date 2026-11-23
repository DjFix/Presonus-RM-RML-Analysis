#include "presonus/mixer/FilterGainFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void FilterGainFormatter::print(Data &data) const {
  Core::CString128 text;
  const double value = data.value;
  if (data.value < 0.1f)
    text.appendFormat("%0.3f", value);
  else if (data.value < 10.f)
    text.appendFormat("%0.2f", value);
  else if (data.value < 100.f)
    text.appendFormat("%0.1f", value);
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
