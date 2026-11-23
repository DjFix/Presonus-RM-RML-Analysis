#pragma once

#include "presonus/mixer/EarlyRefFormatter.hpp"

#include <new>

namespace Presonus::Mixer {

class EarlyRefFormatterT4 final : public EarlyRefFormatter {
public:
  EarlyRefFormatterT4();
  ~EarlyRefFormatterT4() override;

  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }
};

} // namespace Presonus::Mixer
