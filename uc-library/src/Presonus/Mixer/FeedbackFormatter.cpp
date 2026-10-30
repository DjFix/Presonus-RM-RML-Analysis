#include "presonus/mixer/FeedbackFormatter.hpp"
#include "core/public/corestringbuffer.h"
namespace Presonus::Mixer {
FeedbackFormatter::FeedbackFormatter(presonus::mixer::FeedbackFormatterPortTag)
    : Core::Formatter("") {}
FeedbackFormatter::~FeedbackFormatter() = default;
void FeedbackFormatter::print(Data &data) const {
  Core::CString128 text;
  text.appendFormat(data.value < .1f ? "%0.3f" : "%0.2f",
                    static_cast<double>(data.value));
  text.copyTo(data.string, data.size);
}
bool FeedbackFormatter::scan(Data &) const { return false; }
} // namespace Presonus::Mixer
