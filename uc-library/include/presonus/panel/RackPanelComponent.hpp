#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"
#include "presonus/delay_timer.hpp"
#include "presonus/panel/PanelComponent.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <cstdint>
#include <new>
#include <vector>

namespace Presonus::Mixer {
class MixerComponentBase;
}

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
// Single authoritative CCL vector with a compatibility view for the older
// independent adapter API. It never duplicates pointer/container ownership.
class ControlVectorView {
public:
  explicit ControlVectorView(Core::Vector<Presonus::Panel::Control *> &v)
      : values(v) {}
  void push_back(Presonus::Panel::Control *p) {
    if (!values.add(p))
      throw std::bad_alloc();
  }
  void clear() { values.removeAll(); }
  std::size_t size() const { return static_cast<std::size_t>(values.count()); }
  Presonus::Panel::Control *operator[](std::size_t i) const {
    return values.at(static_cast<int>(i));
  }
  auto begin() const { return values.begin(); }
  auto end() const { return values.end(); }
  Core::Vector<Presonus::Panel::Control *> &storage() { return values; }

private:
  Core::Vector<Presonus::Panel::Control *> &values;
};
} // namespace presonus::rackpanel_port
namespace Presonus::Panel {
// Portable source representation. Ordinary returns, storage and inheritance
// are chosen source-port declarations, pending original declaration evidence.
// No ARM layout, vtable or binary interoperability claim is made.
class PanelTask;
class RackPanelComponent : public presonus::panel_port::PanelCore,
                           public PanelComponent {
private:
  Core::Vector<Control *> meterControls{0, 5}, clipControls{0, 5},
      phantomControls{0, 5};

public:
  // Independent source model: vectors own pointer arrays, never the pointees.
  Core::Vector<PanelTask *> tasks{0, 5};
  Presonus::DelayTimer monitorTimer{1.f}, cueTimer{1.f}, statusTimer{1.f},
      resetTimer{1.f};
  explicit RackPanelComponent(presonus::rackpanel_port::Dependencies &deps)
      : PanelComponent(static_cast<presonus::panel_port::PanelCore &>(*this)),
        meterLEDs(meterControls), clipLEDs(clipControls),
        phantomLEDs(phantomControls), deps(&deps) {}
  RackPanelComponent(Presonus::Mixer::MixerComponentBase &, PanelRegistrar &);
  ~RackPanelComponent() override;
  void bindDependencies(presonus::rackpanel_port::Dependencies &d) {
    deps = &d;
  }
  bool checkMonitorRestore(Presonus::DelayTimer &) const;
  void monitorSource(int, bool);
  void updatePanelStatus();
  void clientsChanged();
  void checkPermissionsPWReset();
  void forceCascadeGlobalParamUpdate();
  void help();
  void attachMeterLEDs();
  void attach48vControls();
  void cleanup();
  void attach48vLEDs();
  void detachLEDs();
  void setupMonitorRadioButton(int);
  void attachDigipots();
  // Independent source-port state/configuration, not recovered ELF methods.
  presonus::rackpanel_port::ControlVectorView meterLEDs, clipLEDs, phantomLEDs;
  int panelStatus = 0;
  // Borrowed bindings. Share the startup timestamp across panel instances as
  // the embedding application shares the original process startup timestamp.
  // The mixer and timestamp must remain alive during synchronous callbacks.
  // The timestamp is required on an unblocked reset check; the mixer and all
  // twelve cascade parameters are required for a forced cascade update.
  Presonus::Mixer::MixerComponentBase *mixer = nullptr;
  std::uint32_t permissionFlags = 0;
  std::uint64_t *permissionStartupMilliseconds = nullptr;
  float savedMonitorValue = 0;
  Core::Portable::Parameter *monitorRadioParameter = nullptr;
  Core::Portable::Parameter *observedParameter = nullptr;

private:
  presonus::rackpanel_port::Dependencies *deps = nullptr;
  presonus::rackpanel_port::Dependencies &dependencies() const {
    if (!deps)
      throw std::logic_error("RackPanel dependencies are not bound");
    return *deps;
  }
};
} // namespace Presonus::Panel
