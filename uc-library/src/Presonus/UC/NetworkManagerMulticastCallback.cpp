#include "presonus/uc/network_manager_services.hpp"
#include "presonus/uc/server.hpp"
#include "presonus/uc/server_registrar.hpp"
#include <cstring>
#include <stdexcept>
namespace {
int signedBits(std::uint32_t bits) {
  int value;
  static_assert(sizeof(value) == sizeof(bits));
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
struct RestoreRoutes {
  Presonus::UC::Event &event;
  std::uint32_t source, target;
  ~RestoreRoutes() {
    event.routeA = source;
    event.routeB = target;
  }
};
const presonus::uc::MulticastServerView &
serverView(const presonus::uc::NetworkManagerState &state,
           const Presonus::UC::Server *identity) {
  for (int i = 0; i < state.multicastServers.count(); ++i) {
    const auto *view = state.multicastServers.at(i);
    if (view && view->identity == identity && view->common && view->dispatchIDs)
      return *view;
  }
  throw std::invalid_argument("live actual-server multicast metadata required");
}
} // namespace
namespace Presonus::UC {
void NetworkManager::onMulticastEvent(const char *address,
                                      unsigned short firstPort,
                                      unsigned short secondPort, int transport,
                                      EventItem *item) {
  (void)secondPort; // Original does not use its encoded third parameter.
  Event &event = item->getData();
  if (event.type == 0x4441 || event.type == 0x4e4f || event.type == 0x444c ||
      event.type == 0x4451)
    return;
  if (!state_.registrar)
    throw std::invalid_argument("live source-backed registrar required");
  Server *server = transport == 0
                       ? state_.registrar->find(signedBits(event.routeA), true)
                       : state_.registrar->find(address, firstPort,
                                                signedBits(event.routeA));
  if (!server)
    return;
  const auto &view = serverView(state_, server);
  const int count = view.dispatchIDs->count();
  if (count == 0)
    return;
  RestoreRoutes restore{event, event.routeA, event.routeB};
  event.routeA = view.common->identifierBits;
  event.routeB = 0;
  for (int i = 0; i < count; ++i) {
    event.routeB = static_cast<std::uint32_t>(view.dispatchIDs->at(i));
    sendEvent(event, 0); // Actual original virtual service; return is ignored.
  }
}
} // namespace Presonus::UC
