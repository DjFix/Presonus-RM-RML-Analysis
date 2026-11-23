#pragma once
#include "core/public/coreformatter.h"

namespace Presonus::Mixer {
class ChDelayFormatter : public Core::Formatter {
public:
  // Portable construction and CCL scan are outside the original print scope.
  ChDelayFormatter() = default;
  void print(Data &data) const override;
};
} // namespace Presonus::Mixer
