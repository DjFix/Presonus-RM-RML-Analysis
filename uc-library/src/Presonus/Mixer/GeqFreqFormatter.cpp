#include "presonus/mixer/GeqFreqFormatter.hpp"
#include "core/public/corestringbuffer.h"

namespace Presonus::Mixer {
void GeqFreqFormatter::print(Data &data) const {
  Core::CString128 text;
  static constexpr const char *frequencies[] = {
      "20",  "25",   "32",   "40",   "50",  "63",   "80",   "100",
      "125", "160",  "200",  "250",  "320", "400",  "500",  "640",
      "800", "1k",   "1.3k", "1.6k", "2k",  "2.5k", "3.2k", "4k",
      "5k",  "6.4k", "8k",   "10k",  "13k", "16k",  "20k"};
  const float value = data.value;
  text.append(value > -1.f && value < 31.f
                  ? frequencies[static_cast<int>(value)]
                  : "Error");
  text.copyTo(data.string, data.size);
}
} // namespace Presonus::Mixer
