#include "presonus/mixer/ScaledTimeFormatter.hpp"
#include "core/public/corestringbuffer.h"
namespace Presonus::Mixer {
ScaledTimeFormatter::ScaledTimeFormatter(
    presonus::mixer::ScaledTimeFormatterPortTag)
    : Core::Formatter("") {}
ScaledTimeFormatter::~ScaledTimeFormatter() = default;
void ScaledTimeFormatter::print(Data &data) const {
  Core::CString128 text;
  text.appendFormat("%0.2f", static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
bool ScaledTimeFormatter::scan(Data &) const { return false; }
} // namespace Presonus::Mixer
