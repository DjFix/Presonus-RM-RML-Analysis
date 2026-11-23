#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT2 final : public DecayTimeFormatter {
public:
  // Typed source-port construction; only the deleting destructor is selected.
  DecayTimeFormatterT2();
  ~DecayTimeFormatterT2() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
