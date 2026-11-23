#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT9 final : public DecayTimeFormatter {
public:
  // Source-port typed registration; only the deleting destructor is selected.
  DecayTimeFormatterT9();
  ~DecayTimeFormatterT9() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
