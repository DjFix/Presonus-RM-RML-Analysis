#pragma once
namespace Presonus::Panel {
// Partial portable source port. Original return declarations, inheritance,
// lifecycle, object layout and ARM ABI remain unresolved. Lookup storage is
// borrowed immutable program-lifetime storage; no ownership transfers.
class GambitPanelRegistrar {
public:
  const char *getPanelPortName();
  const int *getTags(int group, int &count) const;
  int getParamInfoListSizeFromGroup(int group);
};
} // namespace Presonus::Panel
