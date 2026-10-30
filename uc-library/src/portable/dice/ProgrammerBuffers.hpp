#pragma once
#include <array>

namespace presonus::dice::detail {
// Independent shared source-port storage for the observed original TX/RX
// aliases. Original addresses, declared types and complete sizes are unknown.
struct ProgrammerBuffers {
  std::array<unsigned char, 260> transmit{};
  std::array<unsigned char, 260> receive{};
};
inline ProgrammerBuffers &programmerBuffers() {
  static ProgrammerBuffers buffers;
  return buffers;
}
} // namespace presonus::dice::detail
