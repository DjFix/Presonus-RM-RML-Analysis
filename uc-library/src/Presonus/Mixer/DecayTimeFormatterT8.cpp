#include "presonus/mixer/DecayTimeFormatterT8.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT8::DecayTimeFormatterT8()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT8";
}
void DecayTimeFormatterT8::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT8>();
}
} // namespace Presonus::Mixer
