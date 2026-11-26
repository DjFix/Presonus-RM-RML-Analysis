#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/event_factory.hpp"
#include "presonus/uc/multicast_connection.hpp"
namespace Presonus::UC {
struct MulticastConnection::Owned {
  EventFactory factory;
  presonus::uc::BasicConnectionState queue;
  presonus::uc::MulticastConnectionState state;
  explicit Owned(MulticastConnection &connection)
      : queue{&presonus::uc::BasicConnectionSourceAccess::queue(connection),
              &factory,
              &presonus::uc::BasicConnectionSourceAccess::storage(connection)
                   .view},
        state(queue, presonus::uc::sourceAdapterSingleton(),
              presonus::uc::sourceAdapterSingleton().sourcePortState()) {
    state.receivers.resize(0);
    state.group.ip.address[0] = 239;
    state.group.ip.address[1] = 32;
    state.group.ip.address[2] = 4;
    state.group.ip.address[3] = 2;
    state.group.port = 0;
    state.resetMarker = 1;
    state.broadcast.setIP(255, 255, 255, 255, 47809);
  }
};
MulticastConnection::MulticastConnection()
    : BasicConnection(0), owned_(std::make_unique<Owned>(*this)),
      state_(owned_->state) {}
MulticastConnection::MulticastConnection(
    presonus::uc::MulticastSourcePortTag,
    presonus::uc::MulticastConnectionState &state)
    : BasicConnection(state.outgoing), state_(state) {}
MulticastConnection::~MulticastConnection() = default;
} // namespace Presonus::UC
