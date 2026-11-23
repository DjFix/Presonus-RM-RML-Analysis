#pragma once
#include "presonus/mixer/EarlyRefFormatter.hpp"

namespace Presonus::Mixer {
class EarlyRefFormatterT2 final : public EarlyRefFormatter {
public:
  // Source-port typed registration; only the deleting destructor is selected.
  EarlyRefFormatterT2();
  ~EarlyRefFormatterT2() override = default;
  static void registerPrototype();
};
} // namespace Presonus::Mixer
