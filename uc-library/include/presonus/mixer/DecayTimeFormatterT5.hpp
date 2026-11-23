#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT5 final : public DecayTimeFormatter {
public:
  // Typed source-port construction; only the deleting destructor is selected.
  DecayTimeFormatterT5();
  ~DecayTimeFormatterT5() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
