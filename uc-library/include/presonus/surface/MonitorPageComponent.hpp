#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Partial source port using an actual borrowed CCL registry. Original layout,
// inheritance and unencoded return declarations remain unresolved.
class MonitorPageComponent {
public:
  struct SourcePortConstruction {};
  MonitorPageComponent(SourcePortConstruction,
                       Core::Portable::Component &parameters)
      : parameters_(parameters) {}
  // selected must be a live parameter; registry/tags remain stable during the
  // call. Finite ordered intervals avoid int32 increment overflow. Unknown
  // provider overrides/reentrant mutation are outside the validated domain.
  void applyMonitorSelection();
  // Observed native no-op; void is the portable declaration.
  void disconnectMappables();
  void paramChanged(Core::Portable::Parameter *parameter, int message);
  bool monitorSelectionInProgress() const { return selectionBusy_; }
  void radioSelection(Core::Portable::Parameter *selected, int first, int last);

private:
  Core::Portable::Component &parameters_;
  bool selectionBusy_ = false;
};
} // namespace Presonus::Surface
