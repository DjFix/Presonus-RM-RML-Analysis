#pragma once
#include "presonus/mixer/PreDelayFormatter.hpp"

namespace Presonus::Mixer {
class PreDelayFormatterT4 : public PreDelayFormatter {
public:
  PreDelayFormatterT4();
  ~PreDelayFormatterT4() override;
};
} // namespace Presonus::Mixer

namespace presonus::mixer {
// Source-port registration at the mixer's formatter bootstrap boundary.
void registerPreDelayFormatterT4();
} // namespace presonus::mixer
