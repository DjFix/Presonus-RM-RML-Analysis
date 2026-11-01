#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corestringbuffer.h"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/message_attributes.hpp"

namespace Presonus {
class WIFIManager;
}
namespace presonus::network_select {
// Independent application boundary. No original WIFIManager declaration, object
// layout, singleton ownership or hardware implementation is implied.
struct NetworkServices {
  virtual ~NetworkServices() = default;
  virtual void serverNotify(const Presonus::UC::MessageAttributes &) = 0;
  virtual void scan(bool force) = 0;
  virtual void idle() = 0;
  virtual void join(const char *ssid, const char *password) = 0;
  virtual void updateList(Core::Portable::ListParam *,
                          Core::Portable::ListParam *,
                          Core::Portable::ListParam *, bool) = 0;
  virtual void suspendAdaptors(bool) = 0;
  virtual void configureInterface(const char *) = 0;
  virtual const char *managerName(const Presonus::WIFIManager &) const = 0;
  virtual const char *managerSSID(const Presonus::WIFIManager &) const = 0;
  virtual const char *managerIP(const Presonus::WIFIManager &,
                                int interface) = 0;
  virtual const void *find(const char *ssid) = 0;
  virtual bool hasFlag(const void *, const char *) = 0;
  virtual const char *signalText(const void *) const = 0;
};
// Explicit fixture-only timing boundary. Production uses real DelayTimer.
struct FixtureTimer {
  virtual ~FixtureTimer() = default;
  virtual bool longEnough() const = 0;
  virtual void reset() = 0;
  virtual void begin(float) = 0;
};
} // namespace presonus::network_select
namespace Presonus::Mixer {
// Portable source contract using actual CCL. Base/layout and ordinary return
// declarations remain unresolved for the original ARM binary.
class NetworkSelectComponent : public Core::Portable::Component {
public:
  explicit NetworkSelectComponent(presonus::network_select::NetworkServices &s)
      : services(s) {}
  void idleScanning();
  void notify(const Presonus::UC::MessageAttributes &);
  int getWiredNetworkAssignMode() const;
  void networkChanged(const Presonus::WIFIManager &);
  void onIdle() override;
  void adaptorConfigChanged(const Presonus::WIFIManager &);
  void getSelectedSSID(Core::CStringBuffer<64> &);
  void idleTasks();
  void updateNetworkList(bool) const;
  void disconnect();

  // Independent port setup. All borrowed objects must outlive this component.
  void configureTimers(Presonus::DelayTimer &scan,
                       Presonus::DelayTimer &config) {
    scanningTimer = &scan;
    configurationTimer = &config;
    fixtureScan = fixtureConfig = nullptr;
  }
  void configureFixtureTimers(presonus::network_select::FixtureTimer &scan,
                              presonus::network_select::FixtureTimer &config) {
    fixtureScan = &scan;
    fixtureConfig = &config;
  }
  void configureScanningParameter(Core::Portable::Parameter *p) {
    scanning = p;
  }
  const char *portSelection() const { return selection.str(); }
  static void configureFixtureToggle(unsigned char value);

private:
  presonus::network_select::NetworkServices &services;
  Presonus::DelayTimer *scanningTimer = nullptr;
  Presonus::DelayTimer *configurationTimer = nullptr;
  presonus::network_select::FixtureTimer *fixtureScan = nullptr;
  presonus::network_select::FixtureTimer *fixtureConfig = nullptr;
  Core::Portable::Parameter *scanning = nullptr;
  Core::CStringBuffer<64> selection;
};
} // namespace Presonus::Mixer
