#include "presonus/mixer/EarlyRefFormatterT3.hpp"

namespace Presonus::Mixer {
EarlyRefFormatterT3::EarlyRefFormatterT3() { name = "earlyrefT3"; }
EarlyRefFormatterT3::~EarlyRefFormatterT3() = default;
} // namespace Presonus::Mixer

namespace presonus::mixer {
void registerEarlyRefFormatterT3() {
  static const bool registered = [] {
    Core::FormatterRegistry::add<Presonus::Mixer::EarlyRefFormatterT3>();
    return true;
  }();
  (void)registered;
}
} // namespace presonus::mixer
