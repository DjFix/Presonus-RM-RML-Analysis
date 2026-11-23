#pragma once
#include "presonus/mixer/PreDelayFormatter.hpp"

namespace Presonus::Mixer {
class PreDelayFormatterT2 final : public PreDelayFormatter {
public:
  // Source-port typed registration; only the deleting destructor is selected.
  PreDelayFormatterT2();
  ~PreDelayFormatterT2() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer

namespace presonus::mixer {
void registerTaggedDelayAndEarlyRefFormatters();
} // namespace presonus::mixer
