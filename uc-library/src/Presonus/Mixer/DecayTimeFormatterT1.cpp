#include "presonus/mixer/DecayTimeFormatterT1.hpp"
#include "presonus/mixer/DecayTimeFormatterT2.hpp"
#include "presonus/mixer/DecayTimeFormatterT3.hpp"
#include "presonus/mixer/DecayTimeFormatterT4.hpp"
#include "presonus/mixer/DecayTimeFormatterT5.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT1::DecayTimeFormatterT1()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT1";
}
void DecayTimeFormatterT1::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT1>();
}
} // namespace Presonus::Mixer
namespace presonus::mixer {
void registerTaggedDecayTimeFormatters() {
  // The pinned registry stores borrowed pointers. Each typed provider
  // retains one static prototype and appends it on each initializer pass.
  Presonus::Mixer::DecayTimeFormatterT1::registerPrototype();
  Presonus::Mixer::DecayTimeFormatterT2::registerPrototype();
  Presonus::Mixer::DecayTimeFormatterT3::registerPrototype();
  Presonus::Mixer::DecayTimeFormatterT4::registerPrototype();
  Presonus::Mixer::DecayTimeFormatterT5::registerPrototype();
}
} // namespace presonus::mixer
