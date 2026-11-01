#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/uc/client_implementation.hpp"
#include <cstdint>

namespace Presonus::UC {
class NetworkItem;
class ClientRootComponent;
} // namespace Presonus::UC
namespace presonus::mixer {
// Required independent application boundary. None of these views assert the
// original NetworkItem/remote-handler layout, ownership, or return declaration.
class NetworkSetupServices {
public:
  virtual ~NetworkSetupServices() = default;
  virtual int itemKind(const Presonus::UC::NetworkItem &) const = 0;
  virtual int itemFilter(const Presonus::UC::NetworkItem &) const = 0;
  virtual const char *itemName(const Presonus::UC::NetworkItem &) const = 0;
  virtual const char *itemSerial(const Presonus::UC::NetworkItem &) const = 0;
  virtual void itemTitle(const Presonus::UC::NetworkItem &,
                         Core::CStringBuffer<128> &) const = 0;
  virtual Presonus::UC::ClientRootComponent *
  component(const Presonus::UC::NetworkItem &) const = 0;
  virtual Presonus::UC::ClientImplementation &
  eventSender(Presonus::UC::ClientRootComponent &) const = 0;
  virtual void acquire(Presonus::UC::NetworkItem &) = 0;
  virtual void release(Presonus::UC::NetworkItem &, bool) = 0;
  virtual void *mixerForClient(Presonus::UC::ClientRootComponent &) = 0;
  virtual void setRemoteMixer(void *) = 0;
  virtual void remoteIdle() = 0;
  virtual void restoredSelection() = 0;
  virtual void serverParamChanged(Core::Portable::Parameter *, int) = 0;
};
// Independent initialized composition, not recovered original class fields.
// Borrowed services/parameters and optional clock state outlive the component.
struct NetworkSetupState {
  Core::Portable::Component &parameters;
  NetworkSetupServices &services;
  Core::Vector<Presonus::UC::NetworkItem *> items;
  Presonus::UC::NetworkItem *selected = nullptr;
  Core::Portable::Parameter *persistentSelection = nullptr;
  bool hasRemoteHandler = false;
  // Test/application clock injection; nullptr selects the real pinned CCL
  // clock.
  std::int64_t (*milliseconds)() = nullptr;
  std::uint64_t *restoreTicks = nullptr;
};
} // namespace presonus::mixer
namespace Presonus::Mixer {
// Encoded original method identities; ordinary returns and original layout,
// inheritance, lifecycle and ARM32 interoperability remain unresolved.
class NetworkSetupComponent {
public:
  explicit NetworkSetupComponent(presonus::mixer::NetworkSetupState &state)
      : state_(state) {}
  void onIdle();
  int sendEvent(UC::Event &);
  void onNetworkItemAdded(UC::NetworkItem *);
  void selectMixer(UC::NetworkItem *, bool);
  void paramChanged(Core::Portable::Parameter *, int);
  UC::ClientRootComponent *getConnectedClient() const;
  void onNetworkShutdown();
  void checkRestoreMixer();
  void onNetworkItemRemoved(UC::NetworkItem *);
  void syncListParam(int, const Core::Vector<UC::NetworkItem *> &,
                     UC::NetworkItem *) const;

private:
  presonus::mixer::NetworkSetupState &state_;
};
} // namespace Presonus::Mixer
