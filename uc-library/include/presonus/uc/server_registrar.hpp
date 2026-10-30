#pragma once
#include "core/public/corevector.h"
#include <array>
#include <cstdint>

namespace Presonus::UC {
// Independent source-port value composition. Original ServerInfo private
// declarations, field names, layout and ARM ABI remain unresolved.
struct ServerInfo {
  std::uint32_t originalDescriptorSize = 24;
  std::array<const char *, 4> strings{};
  std::uint32_t flags = 0;
};
// Original twenty-byte ARM table has three pure slots. Concrete listener
// mangles and call offsets establish these parameters/order. void returns
// remain portable choices, not original static declaration evidence.
class Server;
class LocalServer;
class IEventHandler;
class INetworkListener {
public:
  virtual void onServerAvailable(int, const ServerInfo &) = 0;
  virtual void onServerUnavailable(int) = 0;
  virtual void onServerChanged(int) = 0;

protected:
  ~INetworkListener() = default;
};
} // namespace Presonus::UC

namespace presonus::uc {
// Borrowed, initialized source-port views; no original class layout assertion.
struct AvailableServerView {
  std::array<const char *, 4> strings{};
  std::uint32_t flags = 0;
  int identifier = 0;
  bool hidden = false;
  // Independent correlated identities and metadata, never original fields.
  Presonus::UC::Server *identity = nullptr;
  Presonus::UC::LocalServer *localIdentity = nullptr;
  Presonus::UC::IEventHandler *handler = nullptr;
  void *registrationContext = nullptr;
  const char *remoteAddress = nullptr;
  std::uint16_t remotePort = 0;
  int remoteTransport = 0;
};
struct ServerRegistrarState {
  Core::Vector<AvailableServerView *> localServers;
  Core::Vector<AvailableServerView *> remoteServers;
  Core::Vector<Presonus::UC::INetworkListener *> listeners;
  // Every notified identity has exactly one live registered metadata view.
  Core::Vector<AvailableServerView *> allServerViews;
};
} // namespace presonus::uc

namespace Presonus::UC {
class ServerRegistrar {
public:
  explicit ServerRegistrar(presonus::uc::ServerRegistrarState &state)
      : state_(state) {}
  bool hasListeners() const;
  bool hasLocalServers() const;
  Server *find(IEventHandler *) const;
  Server *find(void *, bool) const;
  Server *find(int, bool) const;
  Server *find(const char *, unsigned short, int) const;
  void notifyServerAdded(Server *);
  void notifyServerRemoved(Server *);
  void notifyServerChanged(Server *);
  void serverRegistered(LocalServer *);
  void addListener(INetworkListener *);
  void removeListener(INetworkListener *);
  void notifyAvailable(INetworkListener *);

private:
  presonus::uc::ServerRegistrarState &state_;
};
} // namespace Presonus::UC
