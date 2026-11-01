#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/PageComponent.hpp"
#include "presonus/delay_timer.hpp"
#include <cstdint>
namespace Presonus {
class WIFIManager;
}
namespace presonus::surface {
// Independent source-port state, never an ARM object-layout declaration.
struct WifiSetupState {
  std::int32_t listOffset = 0;
  std::int32_t selected = -1;
};
struct WifiScanPhase {
  bool refreshNext = false;
};
// Required app-specific boundaries. No default/no-op production implementation.
// WIFIManager remains opaque: this interface does not invent its
// fields/ownership.
struct WifiSetupDependencies {
  virtual ~WifiSetupDependencies() = default;
  virtual void pageOnShow(bool) = 0;
  virtual void startPasswordInput(Core::Portable::Parameter *, const char *,
                                  const void *completionOwner) = 0;
  virtual void ensureManager() const = 0;
  virtual void updateList(Core::Portable::ListParam *,
                          Core::Portable::ListParam *,
                          Core::Portable::ListParam *, bool) const = 0;
  virtual bool findNetwork(const char *) const = 0;
  virtual bool networkHasFlag(const char *) const = 0;
  virtual const char *managerStatus(const Presonus::WIFIManager &) const = 0;
  virtual const char *managerSSID(const Presonus::WIFIManager &) const = 0;
  virtual const char *managerIP(const Presonus::WIFIManager &) const = 0;
  virtual const char *networkSignal() const = 0;
  virtual void scan(bool) = 0;
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Original scopes/encoded signatures; selected portable
// return/inheritance/state contracts. Original unencoded returns, field layout
// and ARM ABI remain pending.
class WifiSetupComponent : public Core::Portable::Component {
public:
  WifiSetupComponent(presonus::surface::WifiSetupState &state,
                     presonus::surface::WifiScanPhase &phase,
                     presonus::surface::WifiSetupDependencies &dependencies,
                     Presonus::PageComponent &page, Presonus::DelayTimer &timer)
      : state(state), phase(phase), dependencies(dependencies), page(page),
        timer(timer) {}
  void connect();
  void addListOffset(int);
  void paramChanged(Core::Portable::Parameter *, int) override;
  int getMaxListOffset() const;
  void networkChanged(const Presonus::WIFIManager &);
  void getSelectedSSID(Core::CStringBuffer<64> &);
  void updateNetworkList(bool) const;
  void onShow(bool);
  void updateDisplayList();
  void checkNetworkScanning();

private:
  presonus::surface::WifiSetupState &state;
  presonus::surface::WifiScanPhase &phase;
  presonus::surface::WifiSetupDependencies &dependencies;
  Presonus::PageComponent &page;
  Presonus::DelayTimer &timer;
};
} // namespace Presonus::Surface
