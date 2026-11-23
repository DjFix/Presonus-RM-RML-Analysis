#include "presonus/mixer/StereoSpreadFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void StereoSpreadFormatter::print(Data &data) const {
  Core::CString128 text;
  text.appendFormat(data.value < 0.1f ? "%0.3f" : "%0.2f",
                    static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
