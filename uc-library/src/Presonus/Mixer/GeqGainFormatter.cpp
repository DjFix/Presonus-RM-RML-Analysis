#include "presonus/mixer/GeqGainFormatter.hpp"
#include "core/public/corestringbuffer.h"
namespace Presonus::Mixer {
GeqGainFormatter::GeqGainFormatter(presonus::mixer::GeqGainFormatterPortTag)
    : Core::Formatter("") {}
GeqGainFormatter::~GeqGainFormatter() = default;
void GeqGainFormatter::print(Data &data) const {
  Core::CString128 text;
  text.appendFormat("%1.1f", static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
bool GeqGainFormatter::scan(Data &) const { return false; }
} // namespace Presonus::Mixer
