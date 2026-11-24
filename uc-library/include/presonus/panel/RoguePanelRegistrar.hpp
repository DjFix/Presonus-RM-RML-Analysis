#pragma once
namespace Presonus::Panel {
// Partial portable source port. Original return declarations, inheritance,
// lifecycle, object layout and ARM ABI remain unresolved. Lookup storage is
// borrowed immutable program-lifetime storage; no ownership transfers.
class RoguePanelRegistrar {
public:
  const char *getPanelPortName();
  const char *getLcdPortName();
  const int *getTags(int group, int &count) const;
  int getParamInfoListSizeFromGroup(int group);
  // Portable no-op; the original return and dispatch declarations remain
  // unresolved.
  void muteCS1TrafficForNOAAArmUpdate();
};
} // namespace Presonus::Panel
