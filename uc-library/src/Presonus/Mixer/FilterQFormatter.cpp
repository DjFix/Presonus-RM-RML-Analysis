#include "presonus/mixer/FilterQFormatter.hpp"
#include "core/public/corestringbuffer.h"
namespace Presonus::Mixer {
FilterQFormatter::FilterQFormatter(presonus::mixer::FilterQFormatterPortTag)
    : Core::Formatter("") {}
FilterQFormatter::~FilterQFormatter() = default;
void FilterQFormatter::print(Data &data) const {
  Core::CString128 text;
  text.appendFormat("%0.2f", static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
bool FilterQFormatter::scan(Data &) const { return false; }
} // namespace Presonus::Mixer
