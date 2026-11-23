#include "presonus/mixer/DecayTimeFormatterT3.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT3::DecayTimeFormatterT3()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT3";
}
void DecayTimeFormatterT3::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT3>();
}
} // namespace Presonus::Mixer
