#pragma once
#include "presonus/panel/control.hpp"
namespace presonus::panel {
struct TemperatureSourcePort {};
} // namespace presonus::panel
namespace Presonus::Panel {
// Real original Control base. Independent construction, no original lifecycle.
class TemperatureControl : public Control {
public:
  TemperatureControl(presonus::panel::TemperatureSourcePort, int tag)
      : Control(tag) {}
  // Original ordinary return declarations remain unencoded and provisional.
  void receiveValue(int) override;
  void *castTo(int) override;
};
} // namespace Presonus::Panel
