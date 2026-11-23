#include "presonus/mixer/DecayTimeFormatterT9.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT9::DecayTimeFormatterT9()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT9";
}
void DecayTimeFormatterT9::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT9>();
}
} // namespace Presonus::Mixer
