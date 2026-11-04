#pragma once
#include <array>
#include <cstdint>
namespace presonus::mixer {
// Independent source-port record. Original return declaration and ARM ABI
// unresolved.
struct AudioSetupRecord {
  std::array<std::uint32_t, 14> observedWords;
};
} // namespace presonus::mixer
