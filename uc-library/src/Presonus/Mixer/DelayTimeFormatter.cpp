#include "presonus/mixer/DelayTimeFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void DelayTimeFormatter::print(Data &data) const {
  Core::CString128 text;
  if (data.value < 10.f)
    text.appendFormat("%0.2f", static_cast<double>(data.value));
  else if (data.value < 100.f)
    text.appendFormat("%0.1f", static_cast<double>(data.value));
  else if (data.value < 1000.f)
    text.appendFormat("%0.0f", static_cast<double>(data.value));
  else
    text.appendFormat("%0.2fK", static_cast<double>(data.value / 1000.f));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
