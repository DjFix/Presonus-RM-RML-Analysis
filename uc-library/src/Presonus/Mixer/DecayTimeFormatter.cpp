#include "presonus/mixer/DecayTimeFormatter.hpp"
#include "core/public/corestringbuffer.h"
namespace Presonus::Mixer {
DecayTimeFormatter::DecayTimeFormatter(presonus::mixer::FormatterPortTag)
    : Core::Formatter("") {}
DecayTimeFormatter::~DecayTimeFormatter() = default;
void DecayTimeFormatter::print(Data &data) const {
  Core::CString128 text;
  text.appendFormat("%0.2f", static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
bool DecayTimeFormatter::scan(Data &) const { return false; }
} // namespace Presonus::Mixer
