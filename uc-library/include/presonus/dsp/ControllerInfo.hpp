#pragma once
#include "presonus/dsp/Controller.hpp"
namespace Presonus {
// Borrowed writable buffer. Explicit portable representation, not ARM layout
// or recovered original field declarations. Capacity is nonnegative.
struct StringResult {
  char *buffer;
  int capacity;
};
namespace Dsp {
// Named source-port representation of the six copied native words and optional
// extension. Pointers borrow descriptor-owned CCL strings. byteSize models the
// native caller +0x18 word independently of this host structure's sizeof.
struct ParamInfo {
  int tag = 0;
  const char *text0 = nullptr;
  const char *text1 = nullptr;
  std::uint32_t flags = 0, word10 = 0, word14 = 0;
  std::uint32_t byteSize = 32;
  const char *text2 = nullptr;
};
} // namespace Dsp
} // namespace Presonus
