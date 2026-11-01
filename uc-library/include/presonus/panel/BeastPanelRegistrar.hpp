#pragma once

#include <cstdint>

namespace Presonus::Panel {
// Portable source port of the observed getTags behavior. The pointer return,
// pointee type/constness and this minimal class are source-port choices; the
// original return declaration, inheritance, object layout and ARM ABI are
// unknown.
class BeastPanelRegistrar {
public:
  const std::int32_t *getTags(int group, int &count) const;
};
} // namespace Presonus::Panel
