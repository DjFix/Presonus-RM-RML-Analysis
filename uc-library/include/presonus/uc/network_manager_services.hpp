#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corebuffer.h"
#include "core/public/corelinkedlist.h"
#include "core/public/corevector.h"
#include "presonus/uc/data_codecs.hpp"
#include "presonus/uc/event_dispatcher.hpp"
#include <cstdint>

namespace Presonus::UC {
class Connection;
class ConnectionHandler;
class IConnection;
class IDataChannel;
class INetworkListener;
class INetworkErrorReporter;
class ServerRegistrar;
class Server;
struct DiscoveryDescriptor;
struct ServerInfo;
struct ServerContextInfo;
// Independent value composition for the original-named parameter type.
// Field declarations/layout and original MessageEvent construction unresolved.
struct MessageEvent {
  Event header{};
  const void *data = nullptr;
  std::uint32_t sizeBits = 0;
};
// Measured primary interface: 31 slots including inherited handleEvent.
// Return spellings below are portable declaration choices, not recovered ABI.
class INetworkManager : public IEventHandler {
public:
  virtual int startup(unsigned char) = 0;
  virtual int shutdown() = 0;
  virtual int setPortNumber(unsigned short, unsigned short, int) = 0;
  virtual int setLocalName(const char *) = 0;
  virtual int setNetworkPriority(int) = 0;
  virtual int registerListener(INetworkListener *) = 0;
  virtual int unregisterListener(INetworkListener *) = 0;
  virtual int registerServer(int &, IEventHandler *, const ServerInfo &,
                             int) = 0;
  virtual int unregisterServer(IEventHandler *) = 0;
  virtual int updateServer(IEventHandler *) = 0;
  virtual int addRemoteServer(int &, const char *, unsigned short,
                              unsigned short, int, const ServerInfo &) = 0;
  virtual int removeRemoteServer(int) = 0;
  virtual int registerHandler(int &, IEventHandler *) = 0;
  virtual int unregisterHandler(IEventHandler *) = 0;
  virtual int sendEvent(const Event &, int) = 0;
  virtual int sendMulticastEvent(const Event &) = 0;
  virtual int setMulticastMapping(int, int, unsigned char, unsigned char) = 0;
  virtual int processIdle() = 0;
  virtual int getServerContextInfo(ServerContextInfo &, int) = 0;
  virtual int addExternalConnection(IConnection *&, IDataChannel *, int,
                                    unsigned char, IEventHandler *) = 0;
  virtual int updateExternalConnection(IDataChannel *, int) = 0;
  virtual int removeExternalConnection(IDataChannel *) = 0;
  virtual int rescanAll(unsigned char) = 0;
  virtual int resetConnection() = 0;
  virtual int addErrorReporter(INetworkErrorReporter *) = 0;
  virtual int removeErrorReporter(INetworkErrorReporter *) = 0;
  virtual int simulateConnectionErrors() = 0;
  virtual int waitForOutgoingEvents(int) = 0;
  virtual int suspendNetworkAdapters(unsigned char) = 0;
  virtual int isSendingFromExternalConnection(int) = 0;

protected:
  ~INetworkManager() = default;
};
class IDiscoveryReplyHandler {
public:
  virtual void onRegistrationCompleted(void *) = 0;
  virtual void onServerAdded(void *, const DiscoveryDescriptor &) = 0;
  virtual void onServerRemoved(void *) = 0;
  virtual void onServerChanged(void *, const char *) = 0;

protected:
  ~IDiscoveryReplyHandler() = default;
};
class IConnectionErrorHandler {
public:
  virtual void onConnectionError(Connection *, bool) = 0;

protected:
  ~IConnectionErrorHandler() = default;
};
class IMulticastReceiver {
public:
  virtual void onMulticastEvent(const char *, unsigned short, unsigned short,
                                int, EventItem *) = 0;

protected:
  ~IMulticastReceiver() = default;
};
} // namespace Presonus::UC
namespace presonus::uc {
// Independent initialized state. No original private member/layout assertion.
// Dispatcher/factory and their registered codecs must be actual source-backed
// providers. All views return live typed storage, not callback success stubs.
// Explicit application-side discovery dependency; no default success provider.
class NetworkDiscoveryControl {
public:
  virtual void startListening() = 0;
  virtual void stopListening() = 0;
  virtual ~NetworkDiscoveryControl() = default;
};
struct ServerState;
// Independent borrowed metadata joining an actual Server identity and its real
// source-port state to genuine CCL dispatch-ID storage. No original fields,
// object layout, ownership or constructor claim. Every found server needs one
// matching live view; IDs remain stable/nonreentrant during dispatch.
struct MulticastServerView {
  Presonus::UC::Server *identity = nullptr;
  const ServerState *common = nullptr;
  const Core::Vector<int> *dispatchIDs = nullptr;
};
struct NetworkManagerState {
  Presonus::UC::EventDispatcher &dispatcher;
  Presonus::UC::EventFactory &factory;
  Core::Vector<Presonus::UC::IEventHandler *> handlers;
  Core::LinkedList<Presonus::UC::EventItem *> pendingChunks;
  void *context = nullptr;
  const Presonus::UC::MessageEvent &(*messageView)(
      void *, const Presonus::UC::Event &) = nullptr;
  Presonus::UC::MessageEvent &(*messageItemView)(
      void *, Presonus::UC::EventItem &) = nullptr;
  const Presonus::UC::MessageChunkEvent &(*chunkView)(
      void *, const Presonus::UC::Event &) = nullptr;
  Core::IO::Buffer &(*storage)(void *, Presonus::UC::EventItem &) = nullptr;
  void (*storeFlags)(void *, Presonus::UC::EventItem &, int) = nullptr;
  void (*reportOversized)(void *) = nullptr;
  // Independent initialized source-port state, not recovered ARM fields.
  Core::Threads::Lock errorReporterLock;
  std::int32_t startedCount = 0;
  // Independent source-port configuration; original private fields unresolved.
  std::uint8_t primaryPortFlag = 0;
  std::uint8_t secondaryPortFlag = 0;
  std::uint16_t firstPort = 0;
  std::uint16_t secondPort = 0;
  std::int32_t threadPriority = 2;
  std::int32_t processInterval = 5;
  std::uint32_t adapterInterval = 1000;
  Core::Threads::Thread *processThread = nullptr;
  Presonus::UC::ServerRegistrar *registrar = nullptr;
  Core::Vector<MulticastServerView *> multicastServers;
  NetworkDiscoveryControl *discovery = nullptr;
  Presonus::UC::ConnectionHandler *connectionHandler = nullptr;
  Core::LinkedList<Presonus::UC::INetworkErrorReporter *> errorReporters;
};
} // namespace presonus::uc
namespace Presonus::UC {
// Original measured five-base order. This partial source class intentionally
// remains abstract; unsupported services have no fake success implementation.
class NetworkManager : public INetworkManager,
                       public IDiscoveryReplyHandler,
                       public IConnectionErrorHandler,
                       public IMulticastReceiver,
                       public Core::Portable::Singleton<NetworkManager> {
public:
  NetworkManager(); // Original C1/C2 remain undefined/unready.
  explicit NetworkManager(presonus::uc::NetworkManagerState &state)
      : state_(state) {}
  virtual ~NetworkManager() = default; // Independent borrowed-state lifetime.
  // Original primary table appends these six secondary-base overrides after
  // D1/D0. Pure declarations preserve the slots without fabricating bodies.
  void onRegistrationCompleted(void *) override;
  void onServerAdded(void *, const DiscoveryDescriptor &) override = 0;
  void onServerRemoved(void *) override = 0;
  void onServerChanged(void *, const char *) override;
  void onConnectionError(Connection *, bool) override = 0;
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        EventItem *) override;
  int setPortNumber(unsigned short, unsigned short, int) override;
  int setNetworkPriority(int) override;
  int isSendingFromExternalConnection(int) override;
  int registerListener(INetworkListener *) override;
  int unregisterListener(INetworkListener *) override;
  int registerHandler(int &, IEventHandler *) override;
  int unregisterHandler(IEventHandler *) override;
  int sendEvent(const Event &, int) override;
  int handleEvent(void *, const Event &) override;
  int sendChunks(const MessageEvent &);
  bool hasOutgoingEvents();
  // Ordinary return declarations remain unresolved in the original.
  Core::Threads::Lock *getLock();
  bool isStarted() const;
  int addErrorReporter(INetworkErrorReporter *) override;
  int removeErrorReporter(INetworkErrorReporter *) override;

private:
  presonus::uc::NetworkManagerState &state_;
};
} // namespace Presonus::UC
