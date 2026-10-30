#include "presonus/mixer_dsp/Formatters.hpp"
#include "Power.hpp"
#include "core/public/corestringbuffer.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
namespace Presonus::Dsp {
FreqFormatter::FreqFormatter(bool option)
    : Core::Formatter(option ? "freq.0" : "freq"), sourceOption_(option) {}
GainDBFormatter::GainDBFormatter(bool option)
    : Core::Formatter(option ? "gain.db" : "gain.db.value"),
      sourceOption_(option) {}
TimeFormatter::TimeFormatter() : Core::Formatter("time") {}
EQQFormatter::EQQFormatter() : Core::Formatter("eqq") {}
TimeFormatter::TimeFormatter(FormatterSourceTag) : Core::Formatter("") {}
FreqFormatter::FreqFormatter(FormatterSourceTag, bool option)
    : Core::Formatter(""), sourceOption_(option) {}
GainDBFormatter::GainDBFormatter(FormatterSourceTag, bool option)
    : Core::Formatter(""), sourceOption_(option) {}
RatioFormatter::RatioFormatter() : Core::Formatter("ratio") {}
RatioFormatter::RatioFormatter(FormatterSourceTag) : Core::Formatter("") {}
EQQFormatter::EQQFormatter(FormatterSourceTag) : Core::Formatter("") {}
TimeFormatter::~TimeFormatter() = default;
FreqFormatter::~FreqFormatter() = default;
GainDBFormatter::~GainDBFormatter() = default;
RatioFormatter::~RatioFormatter() = default;
EQQFormatter::~EQQFormatter() = default;
void EQQFormatter::print(Data &d) const {
  const float v = d.value + d.value;
  std::sprintf(d.string, "%.02f", static_cast<double>(v));
}
bool EQQFormatter::scan(Data &d) const {
  float v = 0;
  if (!Core::FloatFormatter::getFloatValue(v, d.string))
    return false;
  d.value = v * 0.5f;
  return true;
}
void RatioFormatter::print(Data &d) const {
  if (d.value == d.range->maxValue && d.value >= 50.f)
    std::sprintf(d.string, "%s:1", "inf");
  else
    std::sprintf(d.string, "%2.1f:1", static_cast<double>(d.value));
}
bool RatioFormatter::scan(Data &d) const {
  if (d.string && std::strstr(d.string, "inf") && d.range->maxValue >= 50.f) {
    d.value = d.range->maxValue;
    return true;
  }
  return Core::FloatFormatter::getFloatValue(d.value, d.string);
}
void TimeFormatter::print(Data &d) const {
  const float v = d.value;
  if (v < 0.01f)
    std::sprintf(d.string, "%1.2f ms", static_cast<double>(v * 1000.f));
  else if (v < 0.1f)
    std::sprintf(d.string, "%2.1f ms", static_cast<double>(v * 1000.f));
  else if (v < 1.f)
    std::sprintf(d.string, "%3.0f ms", static_cast<double>(v * 1000.f));
  else
    std::sprintf(d.string, "%1.2f s", static_cast<double>(v));
}
bool TimeFormatter::scan(Data &d) const {
  float v = 0;
  if (!Core::FloatFormatter::getFloatValue(v, d.string))
    return false;
  if (!(std::strchr(d.string, 's') && !std::strstr(d.string, "ms")))
    v = v * 0.001f;
  d.value = v;
  return true;
}
void FreqFormatter::print(Data &d) const {
  float v = d.value;
  const char *format;
  if (v >= 1000.f) {
    v = v / 1000.f;
    format = sourceOption_ ? "%.0f kHz" : "%.02f kHz";
  } else if (v >= 100.f)
    format = sourceOption_ ? "%.0f Hz" : "%.01f Hz";
  else
    format = sourceOption_ ? "%.0f Hz" : "%.02f Hz";
  std::sprintf(d.string, format, static_cast<double>(v));
}
bool FreqFormatter::scan(Data &d) const {
  float v = 0;
  if (!Core::FloatFormatter::getFloatValue(v, d.string))
    return false;
  if (std::strchr(d.string, 'k'))
    v = v * 1000.f;
  d.value = v;
  return true;
}
namespace {
float word(std::uint32_t w) {
  float v;
  std::memcpy(&v, &w, 4);
  return v;
}
} // namespace
bool GainDBFormatter::scan(Data &d) const {
  float v = 0;
  if (!Core::FloatFormatter::getFloatValue(v, d.string))
    return false;
  d.value =
      v < -144.f
          ? word(864517951u)
          : presonus::dsp::detail::sourcePowf(10.f, v * word(1028443341u));
  return true;
}
void GainDBFormatter::print(Data &d) const {
  Core::CStringBuffer<128> text;
  if (d.value < word(864528178u)) {
    text.append("-oo");
    if (sourceOption_)
      text.append(" dB");
  } else {
    float db = d.value < word(864517951u) ? -144.f : ::log10f(d.value) * 20.f;
    const float scaled = db < 0.f ? db * 10.f - 0.5f : db * 10.f + 0.5f;
    db = static_cast<float>(static_cast<int>(scaled)) * 0.1f;
    if (db == 0.f)
      text.append("0 dB");
    else {
      text.appendFormat(db > 0.f ? "+%.1f" : "%.1f", static_cast<double>(db));
      if (sourceOption_)
        text.append(" dB");
    }
  }
  text.copyTo(d.string, d.size);
}
} // namespace Presonus::Dsp
