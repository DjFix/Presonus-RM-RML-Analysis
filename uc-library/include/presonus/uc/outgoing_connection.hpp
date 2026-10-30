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
  static OutgoingConnection *cast(Connection *);
  int getType() const override;
  // Explicit unsupported original overrides, not production stub bodies.
  bool process(bool) override = 0;
  bool reset() override = 0;
};
} // namespace Presonus::UC
