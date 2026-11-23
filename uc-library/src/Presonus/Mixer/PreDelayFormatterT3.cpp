#include "presonus/mixer/PreDelayFormatterT3.hpp"

namespace Presonus::Mixer {
PreDelayFormatterT3::PreDelayFormatterT3() { name = "predelayT3"; }
PreDelayFormatterT3::~PreDelayFormatterT3() = default;
} // namespace Presonus::Mixer

namespace presonus::mixer {
void registerPreDelayFormatterT3() {
  static const bool registered = [] {
    Core::FormatterRegistry::add<Presonus::Mixer::PreDelayFormatterT3>();
    return true;
  }();
  (void)registered;
}
} // namespace presonus::mixer
