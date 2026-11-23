#pragma once
#include "presonus/mixer/EarlyRefFormatter.hpp"

namespace Presonus::Mixer {
class EarlyRefFormatterT3 : public EarlyRefFormatter {
public:
  EarlyRefFormatterT3();
  ~EarlyRefFormatterT3() override;
};
} // namespace Presonus::Mixer

namespace presonus::mixer {
// Source-port registration at the mixer's formatter bootstrap boundary.
void registerEarlyRefFormatterT3();
} // namespace presonus::mixer
