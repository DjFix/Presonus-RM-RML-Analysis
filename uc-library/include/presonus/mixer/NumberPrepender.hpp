#pragma once
#include "core/public/coreformatter.h"
#include <cstdint>

namespace Presonus::Mixer {
class NumberPrepender : public Core::Formatter {
public:
  // Portable construction and CCL scan are outside the original print scope.
  explicit NumberPrepender(std::uint8_t prefix) : prefix_(prefix) {}
  void print(Data &data) const override;

private:
  std::uint8_t prefix_;
};
} // namespace Presonus::Mixer
