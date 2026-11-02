#pragma once
#include "core/network/corenetwork.h"
#include "core/portable/corecomponent.h"
#include "core/portable/gui/corelistview.h"
#include "presonus/delay_timer.hpp"
namespace Presonus {
class WIFIManager;
namespace UC {
class NetworkItem;
}
} // namespace Presonus
namespace presonus::surface {
// Independent application boundaries. Opaque app objects and original returns,
// fields and inheritance are deliberately not declared from ELF mangling.
class SurfaceNetworkDependencies {
public:
  virtual ~SurfaceNetworkDependencies() = default;
  virtual int kind(const Presonus::UC::NetworkItem &) const = 0;
  virtual Presonus::UC::NetworkItem *
  associatedItem(const Presonus::UC::NetworkItem &) const = 0;
  virtual void title(const Presonus::UC::NetworkItem &,
                     Core::CStringBuffer<128> &) const = 0;
  virtual const char *host(const Presonus::UC::NetworkItem &) const = 0;
  virtual int mappingCount() const = 0;
  virtual const char *mappingName(int) const = 0;
  virtual int targetType() const = 0;
  virtual bool stored(const char *, Presonus::UC::NetworkItem *) const = 0;
  virtual void acquire(Presonus::UC::NetworkItem *) = 0;
  virtual void release(Presonus::UC::NetworkItem *, bool) = 0;
  virtual void *component(Presonus::UC::NetworkItem *) = 0;
  virtual void *mixerCast(void *) = 0;
  virtual void *dawCast(void *) = 0;
  virtual void setMixer(void *) = 0;
  virtual void setDAW(void *) = 0;
  virtual void setTransport(void *) = 0;
  virtual void itemInfo(int, Presonus::UC::NetworkItem *) = 0;
  virtual void storeSelected(const char *, Presonus::UC::NetworkItem *,
                             int) = 0;
  virtual void setNetworkRoot(Core::Portable::Component *) = 0;
  virtual void selectModelItem(Presonus::UC::NetworkItem *) = 0;
  virtual int wiredAssignMode() const = 0;
  virtual void configureNetwork(const char *) = 0;
  virtual void resumeAdaptors() = 0;
  virtual void enableNetwork(bool) = 0;
  virtual void setupLocalIP() = 0;
};
// Real CCL-backed default. Tests can supply offline address observations.
class SurfaceNetworkProvider {
public:
  virtual ~SurfaceNetworkProvider() = default;
  virtual int localAddresses(Core::Sockets::IPAddress *, int) const;
  virtual bool parseAddress(Core::Sockets::SocketAddress &, const char *) const;
};
struct SurfaceNetworkState {
  Core::Portable::Component &parameters;
  SurfaceNetworkDependencies &dependencies;
  SurfaceNetworkProvider &network;
  Presonus::DelayTimer &timer;
  Core::Vector<Presonus::UC::NetworkItem *> mixers, daws;
  Presonus::UC::NetworkItem *selectedMixer = nullptr;
  Presonus::UC::NetworkItem *selectedDAW = nullptr;
  int selectedMidiMapping = -1;
  Core::Portable::ListViewModel *model = nullptr;
  bool adaptorConfigPending = false;
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Intentional portable composition using upstream Component implementation.
// No original object layout/inheritance/ordinary-return or ARM ABI claim.
class NetworkSetupComponent : public Core::Portable::Component {
public:
  explicit NetworkSetupComponent(presonus::surface::SurfaceNetworkState &state)
      : state_(state) {}
  void syncListParam(int, const Core::Vector<UC::NetworkItem *> &,
                     UC::NetworkItem *) const;
  void onNetworkItemAdded(UC::NetworkItem *);
  void selectMixer(UC::NetworkItem *, int);
  void selectDAW(UC::NetworkItem *, int);
  void setupListModel();
  void adaptorConfigChanged(const Presonus::WIFIManager &);
  void onIdle() override;
  void onNetworkShutdown();
  void onNetworkItemRemoved(UC::NetworkItem *);
  void setupNetworkInfo();

private:
  presonus::surface::SurfaceNetworkState &state_;
};
} // namespace Presonus::Surface
