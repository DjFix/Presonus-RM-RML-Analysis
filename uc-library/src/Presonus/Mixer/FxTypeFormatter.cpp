#include "presonus/mixer/FxTypeFormatter.hpp"
#include "presonus/mixer/XmenFormatterInitializer.hpp"

namespace Presonus::Mixer {

FxTypeFormatter::FxTypeFormatter() : NumberPrepender('T') { name = "fxtype"; }

FxTypeFormatter::~FxTypeFormatter() = default;

template <> void XmenFormatterInitializer::addClass<FxTypeFormatter>() {
  static FxTypeFormatter theFormatter;
  Core::FormatterRegistry::add(&theFormatter);
}

} // namespace Presonus::Mixer
