#include "presonus/mixer/EarlyRefFormatterT2.hpp"

namespace Presonus::Mixer {
EarlyRefFormatterT2::EarlyRefFormatterT2() : EarlyRefFormatter() {
  name = "earlyrefT2";
}
void EarlyRefFormatterT2::registerPrototype() {
  Core::FormatterRegistry::add<EarlyRefFormatterT2>();
}
} // namespace Presonus::Mixer
