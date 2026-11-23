#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT3 final : public DecayTimeFormatter {
public:
  // Typed source-port construction; only the deleting destructor is selected.
  DecayTimeFormatterT3();
  ~DecayTimeFormatterT3() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
