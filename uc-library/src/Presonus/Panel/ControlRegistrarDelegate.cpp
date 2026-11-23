#include "presonus/surface/DisplayManager.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"

namespace Presonus::Panel {
void ControlRegistrar::Delegate::faderChanged(const ControlRegistrar &, int,
                                              int, FaderControl *) {}
void ControlRegistrar::Delegate::switchChanged(const ControlRegistrar &, int,
                                               int, bool, SwitchControl *) {}
void ControlRegistrar::Delegate::potChanged(const ControlRegistrar &, int, int,
                                            PotControl *) {}
void ControlRegistrar::Delegate::screenTouched(const ControlRegistrar &,
                                               TouchInputEvent) {}
} // namespace Presonus::Panel
