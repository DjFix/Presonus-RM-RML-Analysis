#pragma once

#include "presonus/mixer/EarlyRefFormatter.hpp"

#include <new>

namespace Presonus::Mixer {

class EarlyRefFormatterT6 final : public EarlyRefFormatter {
public:
  EarlyRefFormatterT6();
  ~EarlyRefFormatterT6() override;

  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }
};

} // namespace Presonus::Mixer
