#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
namespace Presonus::Dsp {
MillisecondsFormatter *MillisecondsFormatter::instance(bool finePrecision) {
  static MillisecondsFormatter theFormatter("ms", false);
  static MillisecondsFormatter theFineFormatter("ms.fine", true);
  return finePrecision ? &theFineFormatter : &theFormatter;
}
} // namespace Presonus::Dsp
