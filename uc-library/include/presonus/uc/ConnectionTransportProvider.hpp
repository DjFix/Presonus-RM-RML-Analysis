#pragma once
#include "core/network/coresocket.h"
#include "presonus/uc/connection_receive.hpp"
#include "presonus/uc/misc_events.hpp"
#include "presonus/uc/owned_data_factory_codec.hpp"
#include "presonus/uc/socket_channel.hpp"
#include <map>

namespace presonus::uc {
// Independent source composition of actual application/CCL providers. This is
// not the firmware's private object layout or legacy CoreSocket interface.
struct ConnectionTransportProvider {
  explicit ConnectionTransportProvider(Presonus::UC::Connection &);
  Presonus::UC::Connection &connection;
  Presonus::UC::IDataChannel *channel =
      nullptr; // borrowed; concrete owner below
  Presonus::UC::EventFactory factory;
  Core::CStringBuffer<256> connectionName;
  Core::IO::Buffer receiveBuffer;
  Core::IO::Buffer writeBuffer;
  ConnectionReceiveState receive;
  std::map<const Presonus::UC::Event *, unsigned short> mappingPorts;
  std::map<const Presonus::UC::Event *,
           const OwnedDataPayload<Presonus::UC::LoopbackQueryEvent> *>
      loopbackQueries;
  bool failed = false;
  std::uint64_t sentBytes = 0, sentEvents = 0;
  void bind(Presonus::UC::IDataChannel *);
};
} // namespace presonus::uc
