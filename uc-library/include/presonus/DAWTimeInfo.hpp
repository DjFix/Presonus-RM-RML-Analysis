#pragma once

#include <cstdint>

namespace Presonus {

// Portable borrowed-state adapter. This declaration does not establish the
// original class layout or original, unencoded return type. The caller supplies
// at least 309 readable bytes representing the observed ARM object state.
class DAWTimeInfo {
public:
  explicit DAWTimeInfo(const std::uint8_t *borrowedState) noexcept
      : borrowedState_(borrowedState) {}

  // unsigned int preserves the full zero-extended ARM r0 observation; the
  // original source return declaration remains unresolved.
  unsigned int isMusicalDisplay() const;

private:
  const std::uint8_t *borrowedState_;
};

} // namespace Presonus
