#pragma once
#include "presonus/uc/multicast_connection.hpp"
namespace presonus::uc {
// Independent source port to actual pinned CCL Socket/IPAddress providers.
// No original legacy CoreSocket/IPAddress interface or mangling credit.
class MulticastDatagramProvider {
public:
  explicit MulticastDatagramProvider(Presonus::UC::MulticastConnection &);
  bool sendTo(const AdapterIPAddress &, const Presonus::UC::Event &);
  bool writeEvent(Core::Sockets::Socket &, const AdapterIPAddress &,
                  const Presonus::UC::Event &);
  bool readEvent(Core::Sockets::Socket &);
  const MulticastConnectionState &sourceState() const { return state_; }
  void bindReceiver(Presonus::UC::IMulticastReceiver &,
                    MulticastReceiveDisposition &);
  static void normalizeAddress(Presonus::UC::AdapterHandler &,
                               AdapterIPAddress &);
  static bool isLocalAddress(Presonus::UC::AdapterHandler &,
                             const AdapterIPAddress &);

private:
  Presonus::UC::MulticastConnection &connection_;
  MulticastConnectionState &state_;
};
} // namespace presonus::uc
