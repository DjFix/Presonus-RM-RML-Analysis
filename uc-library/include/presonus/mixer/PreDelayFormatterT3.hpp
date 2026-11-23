#pragma once
#include "presonus/mixer/PreDelayFormatter.hpp"

namespace Presonus::Mixer {
class PreDelayFormatterT3 : public PreDelayFormatter {
public:
  PreDelayFormatterT3();
  ~PreDelayFormatterT3() override;
};
} // namespace Presonus::Mixer

namespace presonus::mixer {
// Source-port registration at the mixer's formatter bootstrap boundary.
void registerPreDelayFormatterT3();
} // namespace presonus::mixer
