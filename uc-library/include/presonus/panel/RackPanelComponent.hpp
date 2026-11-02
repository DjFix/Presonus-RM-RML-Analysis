#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/delay_timer.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <vector>

namespace Presonus::Panel {
class RackPanelComponent;
}
namespace presonus::rackpanel_port {
// Independent application adapter: does not declare original registrar, mixer,
// delegate or timer layouts. Parameter lookup and edits use real CCL objects.
struct Channel {
  Core::Portable::Component *parameters = nullptr;
  int tag = 0;
};
struct Dependencies {
  virtual ~Dependencies() = default;
  virtual Presonus::Panel::ControlGroup &group(int id) = 0;
  virtual Core::Portable::Component &monitorParameters() = 0;
  virtual const std::vector<Channel> &channels() const = 0;
  virtual int numClients() const = 0;
  virtual void removeDelegate(Presonus::Panel::RackPanelComponent &) = 0;
  virtual void blink(Presonus::Panel::LEDControl &led, int mode) {
    led.setBlinkMode(static_cast<Presonus::Panel::LEDControl::BlinkMode>(mode));
  }
};
} // namespace presonus::rackpanel_port
namespace Presonus::Panel {
// Portable source representation. Ordinary returns, storage and inheritance
// are chosen source-port declarations, pending original declaration evidence.
// No ARM layout, vtable or binary interoperability claim is made.
class RackPanelComponent : public Core::Portable::Component {
public:
  explicit RackPanelComponent(presonus::rackpanel_port::Dependencies &deps)
      : deps(deps) {}
  bool checkMonitorRestore(Presonus::DelayTimer &) const;
  void monitorSource(int, bool);
  void updatePanelStatus();
  void attachMeterLEDs();
  void attach48vControls();
  void cleanup();
  void attach48vLEDs();
  void detachLEDs();
  void setupMonitorRadioButton(int);
  void attachDigipots();
  // Independent source-port state/configuration, not recovered ELF methods.
  std::vector<Control *> meterLEDs, clipLEDs, phantomLEDs;
  int panelStatus = 0;
  float savedMonitorValue = 0;
  Core::Portable::Parameter *monitorRadioParameter = nullptr;
  Core::Portable::Parameter *observedParameter = nullptr;

private:
  presonus::rackpanel_port::Dependencies &deps;
};
} // namespace Presonus::Panel
