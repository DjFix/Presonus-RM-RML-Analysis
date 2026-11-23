#pragma once
#include "core/public/coreformatter.h"

namespace Presonus::Mixer {
class EarlyRefFormatter : public Core::Formatter {
public:
  // Portable construction and CCL scan are outside the original print scope.
  EarlyRefFormatter() = default;
  void print(Data &data) const override;
};
} // namespace Presonus::Mixer
