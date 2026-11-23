#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT4 final : public DecayTimeFormatter {
public:
  // Typed source-port construction; only the deleting destructor is selected.
  DecayTimeFormatterT4();
  ~DecayTimeFormatterT4() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
