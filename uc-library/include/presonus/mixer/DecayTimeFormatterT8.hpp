#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT8 final : public DecayTimeFormatter {
public:
  // Source-port typed registration; only the deleting destructor is selected.
  DecayTimeFormatterT8();
  ~DecayTimeFormatterT8() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
