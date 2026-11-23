#pragma once
#include "core/public/coreformatter.h"

namespace Presonus::Mixer {
class PreDelayFormatter : public Core::Formatter {
public:
  // Portable construction and CCL scan are outside the original print scope.
  PreDelayFormatter() = default;
  void print(Data &data) const override;
};
} // namespace Presonus::Mixer
