#include "presonus/mixer/DecayTimeFormatterT4.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT4::DecayTimeFormatterT4()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT4";
}
void DecayTimeFormatterT4::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT4>();
}
} // namespace Presonus::Mixer
