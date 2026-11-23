#pragma once

#include "presonus/mixer/PreDelayFormatter.hpp"

#include <new>

namespace Presonus::Mixer {

class PreDelayFormatterT5 final : public PreDelayFormatter {
public:
  PreDelayFormatterT5();
  ~PreDelayFormatterT5() override;

  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }
};

} // namespace Presonus::Mixer
