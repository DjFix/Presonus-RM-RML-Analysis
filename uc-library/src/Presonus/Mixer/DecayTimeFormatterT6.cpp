#include "presonus/mixer/DecayTimeFormatterT6.hpp"
#include "presonus/mixer/DecayTimeFormatterT7.hpp"
#include "presonus/mixer/DecayTimeFormatterT8.hpp"
#include "presonus/mixer/DecayTimeFormatterT9.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT6::DecayTimeFormatterT6()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT6";
}
void DecayTimeFormatterT6::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT6>();
}
} // namespace Presonus::Mixer

namespace presonus::mixer {
void registerAdditionalTaggedDecayTimeFormatters() {
  // Append the same static prototypes in native order on every pass.
  Presonus::Mixer::DecayTimeFormatterT6::registerPrototype();
  Presonus::Mixer::DecayTimeFormatterT7::registerPrototype();
  Presonus::Mixer::DecayTimeFormatterT8::registerPrototype();
  Presonus::Mixer::DecayTimeFormatterT9::registerPrototype();
}
} // namespace presonus::mixer
