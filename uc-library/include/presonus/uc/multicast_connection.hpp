#pragma once
#include "core/network/coresocket.h"
#include "presonus/uc/adapter_handler.hpp"
#include "presonus/uc/basic_connection.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <array>
#include <cstdint>
namespace presonus::uc {
struct MulticastSourcePortTag {};
struct SocketBundleState {
  // Source-port owned actual CCL sockets; count0..10, live unique pointers.
  std::array<Core::Sockets::Socket *, 10> sockets{};
  int count = 0;
  SocketBundleState() = default;
  SocketBundleState(const SocketBundleState &) = delete;
  SocketBundleState &operator=(const SocketBundleState &) = delete;
};
} // namespace presonus::uc
namespace Presonus::UC {
class SocketBundle {
public:
  SocketBundle(presonus::uc::MulticastSourcePortTag,
               presonus::uc::SocketBundleState &state)
      : state_(state) {}
  void deleteAll();
  bool isAnyError(int);

private:
  presonus::uc::SocketBundleState &state_;
};
} // namespace Presonus::UC
namespace presonus::uc {
// Independent source composition; no original field/layout/lifecycle claim.
struct MulticastConnectionState {
  MulticastConnectionState(BasicConnectionState &queue,
                           Presonus::UC::AdapterHandler &adapterObject,
                           AdapterHandlerState &adapterStorage)
      : outgoing(queue), adapter(adapterObject), adapterState(adapterStorage),
        unicast(MulticastSourcePortTag{}, unicastStorage),
        multicast(MulticastSourcePortTag{}, multicastStorage) {}
  MulticastConnectionState(const MulticastConnectionState &) = delete;
  MulticastConnectionState &
  operator=(const MulticastConnectionState &) = delete;
  BasicConnectionState &outgoing;
  Presonus::UC::AdapterHandler &adapter;
  AdapterHandlerState &adapterState;
  SocketBundleState unicastStorage, multicastStorage;
  Presonus::UC::SocketBundle unicast, multicast;
  Core::Vector<Presonus::UC::IMulticastReceiver *> receivers;
  AdapterIPAddress group;
  std::uint16_t configuredPort = 0, boundPort = 0;
  std::uint8_t unicastEnabled = 0, multicastEnabled = 0, groupPending = 0;
  std::int64_t pendingSinceMilliseconds = 0;
};
} // namespace presonus::uc
namespace Presonus::UC {
// Original SI RTTI proves BasicConnection base. Current base/this source port
// intentionally omit original virtual lifecycle/table/ARM layout guarantees.
class MulticastConnection : public BasicConnection {
public:
  MulticastConnection(presonus::uc::MulticastSourcePortTag,
                      presonus::uc::MulticastConnectionState &state)
      : BasicConnection(state.outgoing), state_(state) {}
  void makeMulticastSockets(bool);
  void makeUnicastSockets(bool);
  void startUnicastListening();
  void setMulticastGroupPending(bool);
  void addReceiver(IMulticastReceiver *);
  void removeReceiver(IMulticastReceiver *);

private:
  presonus::uc::MulticastConnectionState &state_;
};
} // namespace Presonus::UC
