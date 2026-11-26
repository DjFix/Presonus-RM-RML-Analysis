#pragma once
#include "presonus/uc/socket_channel.hpp"
namespace Presonus::UC {
class OutgoingConnection : public SocketConnection {
public:
  OutgoingConnection(presonus::uc::SocketConnectionSourcePortTag tag,
                     presonus::uc::ConnectionState &state,
                     presonus::uc::BasicConnectionState &outgoing,
                     presonus::uc::SocketConnectionState &socket)
      : SocketConnection(tag, state, outgoing, socket) {}
  OutgoingConnection(ConnectionHandler &, const char *, unsigned short,
                     unsigned short);
  ~OutgoingConnection() override;
  bool activate();
  void deactivate();
  static OutgoingConnection *cast(Connection *);
  int getType() const override;
  // Original-named lifecycle with actual CCL transport; no ARM ABI claim.
  bool process(bool) override;
  bool reset() override;

private:
  std::uint32_t retries_ = 0;
};
} // namespace Presonus::UC
