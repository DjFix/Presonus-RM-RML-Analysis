#pragma once
#include "core/portable/coreparaminfo.h"

#include <cstdint>

namespace Presonus::Panel {
// Portable source port of the observed getTags behavior. The pointer return,
// pointee type/constness and this minimal class are source-port choices; the
// original return declaration, inheritance, object layout and ARM ABI are
// unknown.
class BeastPanelRegistrar {
public:
  // Provisional typed source-port return; original return/constness unresolved.
  const Core::Portable::ParamInfo *getParamInfoListFromGroup(int group);
  // Provisional return declaration; original unencoded return remains pending.
  int getParamInfoListSizeFromGroup(int group);
  const std::int32_t *getTags(int group, int &count) const;
};
} // namespace Presonus::Panel
