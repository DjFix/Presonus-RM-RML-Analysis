#pragma once
#include "presonus/panel/RackPanelComponent.hpp"
namespace Presonus::Panel {
// Independent construction tag. No original constructor, full member layout,
// multiple-inheritance arrangement, exception paths or ARM ABI is established.
struct WolverineSourcePortConstruction {};
// Bounded source port: the native destructors install their own vtables then
// destroy RackPanelComponent. Host C++ performs its own vtable transitions and
// invokes the actual canonical Rack lifecycle; no ARM offsets are reproduced.
class WolverinePanelComponent : public RackPanelComponent {
public:
  WolverinePanelComponent(WolverineSourcePortConstruction,
                          presonus::rackpanel_port::Dependencies &dependencies)
      : RackPanelComponent(dependencies) {}
  ~WolverinePanelComponent() override;
};
} // namespace Presonus::Panel
