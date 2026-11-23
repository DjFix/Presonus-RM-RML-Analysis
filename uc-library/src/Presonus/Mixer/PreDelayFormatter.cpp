#include "presonus/mixer/PreDelayFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void PreDelayFormatter::print(Data &data) const {
  Core::CString128 text;
  text.appendFormat(data.value < 10.f ? "%0.2f" : "%0.1f",
                    static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
