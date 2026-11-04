#pragma once
#include "presonus/mixer_dsp/Dsp.hpp"
#include <array>
namespace Presonus::Dsp {
// Explicit source-port property shapes. Core prefix is actual pinned CCL;
// app payload fields model independently observed native accesses, not ARM ABI.
struct SetupProperty : Core::Property {
  float rate = 0;
  int reserved = 0, inputs = 1, outputs = 1, precision = 0;
  SetupProperty() : Property(1399157877, sizeof(SetupProperty)) {}
};
struct ChannelProperty : Core::Property {
  int channel = 0;
  struct Entry {
    int band = -1;
    std::array<float, 5> coefficients{};
  };
  std::array<Entry, 8> entries{};
  int count = 0;
  ChannelProperty() : Property(0, sizeof(ChannelProperty)) {}
};
} // namespace Presonus::Dsp
