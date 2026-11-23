#include "presonus/mixer/NumberPrepender.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void NumberPrepender::print(Data &data) const {
  Core::CString128 text;
  const float number = data.value + 1.f;
  if (number >= -2147483648.f && number < 2147483648.f)
    text.appendFormat("%c%d", static_cast<int>(prefix_),
                      static_cast<int>(number));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
