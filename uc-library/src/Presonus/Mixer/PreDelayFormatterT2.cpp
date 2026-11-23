#include "presonus/mixer/PreDelayFormatterT2.hpp"
#include "presonus/mixer/EarlyRefFormatterT2.hpp"

namespace Presonus::Mixer {
PreDelayFormatterT2::PreDelayFormatterT2() : PreDelayFormatter() {
  name = "predelayT2";
}
void PreDelayFormatterT2::registerPrototype() {
  Core::FormatterRegistry::add<PreDelayFormatterT2>();
}
} // namespace Presonus::Mixer

namespace presonus::mixer {
void registerTaggedDelayAndEarlyRefFormatters() {
  // Append the same static prototypes in native order on every pass.
  Presonus::Mixer::PreDelayFormatterT2::registerPrototype();
  Presonus::Mixer::EarlyRefFormatterT2::registerPrototype();
}
} // namespace presonus::mixer
