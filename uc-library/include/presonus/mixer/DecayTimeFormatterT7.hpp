#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT7 final : public DecayTimeFormatter {
public:
  // Source-port typed registration; only the deleting destructor is selected.
  DecayTimeFormatterT7();
  ~DecayTimeFormatterT7() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
