#include "presonus/mixer/DecayTimeFormatterT2.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT2::DecayTimeFormatterT2()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT2";
}
void DecayTimeFormatterT2::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT2>();
}
} // namespace Presonus::Mixer
