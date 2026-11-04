#include "presonus/uc/server.hpp"

namespace Presonus::UC {
Server::Server()
    : ownedState_(std::make_unique<presonus::uc::ServerState>()),
      state_(*ownedState_) {}
// storage_ is real CCL storage. The raw native vptr write is an ABI exclusion.
Server::~Server() = default;
RemoteServer::RemoteServer()
    : RemoteServer(std::make_unique<presonus::uc::RemoteServerState>()) {}
RemoteServer::RemoteServer(
    std::unique_ptr<presonus::uc::RemoteServerState> state)
    : Server(presonus::uc::ServerSourcePortTag{}, state->common),
      ownedRemote_(std::move(state)), remote_(*ownedRemote_) {}
RemoteServer::~RemoteServer() = default;
} // namespace Presonus::UC
