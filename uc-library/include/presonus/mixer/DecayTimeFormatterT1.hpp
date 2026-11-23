#pragma once
#include "presonus/mixer/DecayTimeFormatter.hpp"

namespace Presonus::Mixer {
class DecayTimeFormatterT1 final : public DecayTimeFormatter {
public:
  // Typed source-port construction; only the deleting destructor is selected.
  DecayTimeFormatterT1();
  ~DecayTimeFormatterT1() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
namespace presonus::mixer {
// Register the selected typed prototypes in the observed application order.
void registerTaggedDecayTimeFormatters();
} // namespace presonus::mixer
