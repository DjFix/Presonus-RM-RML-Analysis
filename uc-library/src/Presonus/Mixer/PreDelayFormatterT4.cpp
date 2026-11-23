#include "presonus/mixer/PreDelayFormatterT4.hpp"

namespace Presonus::Mixer {
PreDelayFormatterT4::PreDelayFormatterT4() { name = "predelayT4"; }
PreDelayFormatterT4::~PreDelayFormatterT4() = default;
} // namespace Presonus::Mixer

namespace presonus::mixer {
void registerPreDelayFormatterT4() {
  static const bool registered = [] {
    Core::FormatterRegistry::add<Presonus::Mixer::PreDelayFormatterT4>();
    return true;
  }();
  (void)registered;
}
} // namespace presonus::mixer
