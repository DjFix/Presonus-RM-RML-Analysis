#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT6 final : public DecayTimeFormatter {
public:
  // Source-port typed registration; only the deleting destructor is selected.
  DecayTimeFormatterT6();
  ~DecayTimeFormatterT6() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer

namespace presonus::mixer {
void registerAdditionalTaggedDecayTimeFormatters();
} // namespace presonus::mixer
