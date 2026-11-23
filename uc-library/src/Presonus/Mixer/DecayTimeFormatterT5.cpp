#include "presonus/mixer/DecayTimeFormatterT5.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT5::DecayTimeFormatterT5()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT5";
}
void DecayTimeFormatterT5::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT5>();
}
} // namespace Presonus::Mixer
