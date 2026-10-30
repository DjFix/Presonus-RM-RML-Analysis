#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include "core/public/corestringbuffer.h"
#include <cmath>
#include <cstdio>
#include <cstring>
namespace Presonus::Dsp {
const char *GainFormatter::nameFromPrecision(int precision, bool label) {
  switch (precision) {
  case 0:
    return label ? "gain.0" : "gain.0.value";
  case 1:
    return label ? "gain.1" : "gain.1.value";
  case 2:
    return label ? "gain" : "gain.value";
  default:
    return nullptr;
  }
}
GainFormatter::GainFormatter(int precision, bool label)
    : Core::Formatter(nameFromPrecision(precision, label)),
      sourcePrecision_(precision), sourceLabel_(label) {}
const char *PanFormatter::nameFromMode(Mode mode) {
  return static_cast<int>(mode) == 1 ? "pan.100" : "pan";
}
PanFormatter::PanFormatter(Mode mode)
    : Core::Formatter(nameFromMode(mode)), sourceMode_(static_cast<int>(mode)) {
}

BPMFormatter::BPMFormatter(bool label)
    : Core::Formatter(label ? "bpm" : "bpm.value"), sourceLabel_(label) {}
CounterFormatter::CounterFormatter(int width)
    : Core::Formatter("count"), sourceWidth_(width) {}
BPMFormatter::BPMFormatter(AdditionalFormatterSourceTag, bool label)
    : Core::Formatter(""), sourceLabel_(label) {}
MillisecondsFormatter::MillisecondsFormatter(const char *name,
                                             bool highPrecision)
    : Core::Formatter(name), sourceHighPrecision_(highPrecision) {}
MillisecondsFormatter::MillisecondsFormatter(AdditionalFormatterSourceTag,
                                             bool precision)
    : Core::Formatter(""), sourceHighPrecision_(precision) {}
CounterFormatter::CounterFormatter(AdditionalFormatterSourceTag, int width)
    : Core::Formatter(""), sourceWidth_(width) {}
GainFormatter::GainFormatter(AdditionalFormatterSourceTag, int precision,
                             bool label)
    : Core::Formatter(""), sourcePrecision_(precision), sourceLabel_(label) {}
PanFormatter::PanFormatter(AdditionalFormatterSourceTag, int mode)
    : Core::Formatter(""), sourceMode_(mode) {}
BPMFormatter::~BPMFormatter() = default;
MillisecondsFormatter::~MillisecondsFormatter() = default;
CounterFormatter::~CounterFormatter() = default;
GainFormatter::~GainFormatter() = default;
PanFormatter::~PanFormatter() = default;
bool BPMFormatter::scan(Data &d) const {
  return Core::FloatFormatter::getFloatValue(d.value, d.string);
}
bool MillisecondsFormatter::scan(Data &d) const {
  return Core::FloatFormatter::getFloatValue(d.value, d.string);
}
bool GainFormatter::scan(Data &d) const {
  return Core::FloatFormatter::getFloatValue(d.value, d.string);
}
bool PanFormatter::scan(Data &) const { return false; }
bool CounterFormatter::scan(Data &d) const {
  long long value = 0;
  if (std::sscanf(d.string ? d.string : "", "%lld", &value) != 1)
    return false;
  d.value = static_cast<float>(value);
  return true;
}
void CounterFormatter::print(Data &d) const {
  const int value = static_cast<int>(d.value);
  Core::CStringBuffer<32> format;
  format.appendFormat("%%0%dd", sourceWidth_);
  Core::CStringBuffer<32> text;
  text.appendFormat(format.str(), value);
  text.copyTo(d.string, d.size);
}
void GainFormatter::print(Data &d) const {
  Core::CStringBuffer<32> format;
  format.appendFormat("%%.0%df", sourcePrecision_);
  if (sourceLabel_)
    format.append(" dB");
  std::sprintf(d.string, format.str(), static_cast<double>(d.value));
}
void MillisecondsFormatter::print(Data &d) const {
  Core::CStringBuffer<128> text;
  if (sourceHighPrecision_)
    text.appendFormat(d.value < 10.f ? "%.3f ms" : "%.2f ms",
                      static_cast<double>(d.value));
  else if (d.value < 1.f)
    text.appendFormat("0.%d ms", static_cast<int>(d.value * 10.f));
  else
    text.appendFormat("%.1f ms", static_cast<double>(d.value));
  text.copyTo(d.string, d.size);
}
void BPMFormatter::print(Data &d) const {
  const double adjustment = d.value == 0.f ? 0. : d.value > 0.f ? .5 : -.5;
  const float scaled = d.value * 10000.f;
  const double rounded =
      std::floor(static_cast<double>(scaled) + adjustment) / 10000.;
  Core::CStringBuffer<128> text;
  text.appendFormat("%.4lf", rounded);
  // Original app strips at most two trailing zero characters.
  for (int i = 0; i < 2; ++i) {
    const auto n = std::strlen(text.str());
    if (n == 0 || text.str()[n - 1] != '0')
      break;
    text.truncate(static_cast<int>(n - 1));
  }
  if (sourceLabel_)
    text.append(" BPM");
  text.copyTo(d.string, d.size);
}
void PanFormatter::print(Data &d) const {
  Core::CStringBuffer<128> text;
  if (sourceMode_ != 0) {
    if (d.value <= 0.f)
      text.append("< L >");
    else if (d.value >= 1.f)
      text.append("< R >");
  }
  if (text.str()[0] == 0) {
    const bool left = d.value < .5f;
    const float delta = left ? .5f - d.value : d.value - .5f;
    const float factor = sourceMode_ == 1 ? 200.f : 100.f;
    const float scaled = delta * factor + .5f;
    const int amount = static_cast<int>(scaled);
    if (amount == 0)
      text.append("< C >");
    else
      text.appendFormat(left ? "L %d" : "R %d", amount);
  }
  text.copyTo(d.string, d.size);
}
} // namespace Presonus::Dsp
