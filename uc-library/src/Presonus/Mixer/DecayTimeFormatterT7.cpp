#include "presonus/mixer/DecayTimeFormatterT7.hpp"

namespace Presonus::Mixer {
DecayTimeFormatterT7::DecayTimeFormatterT7()
    : DecayTimeFormatter(presonus::mixer::FormatterPortTag{}) {
  name = "decaytimeT7";
}
void DecayTimeFormatterT7::registerPrototype() {
  Core::FormatterRegistry::add<DecayTimeFormatterT7>();
}
} // namespace Presonus::Mixer
