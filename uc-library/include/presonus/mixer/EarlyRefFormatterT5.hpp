#pragma once

#include "presonus/mixer/EarlyRefFormatter.hpp"

#include <new>

namespace Presonus::Mixer {

class EarlyRefFormatterT5 final : public EarlyRefFormatter {
public:
  EarlyRefFormatterT5();
  ~EarlyRefFormatterT5() override;

  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }
};

} // namespace Presonus::Mixer
