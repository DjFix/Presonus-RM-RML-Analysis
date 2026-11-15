#pragma once
#include "core/portable/coreparaminfo.h"
namespace Presonus::Panel {
// Independent source-port construction; original inheritance/layout unknown.
class WolverinePanelRegistrar {
public:
  // Provisional typed source-port return; original return/constness unresolved.
  const Core::Portable::ParamInfo *getParamInfoListFromGroup(int group);
  // Provisional int models original r0; ordinary return declaration unresolved.
  int getParamInfoListSizeFromGroup(int group);
};
} // namespace Presonus::Panel
