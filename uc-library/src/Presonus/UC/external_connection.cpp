#include "presonus/uc/external_connection.hpp"
namespace Presonus::UC {
void ExternalConnection::adjustRouting(Event &event, bool direction) {
  if (state_.orientation) {
    if (direction)
      event.routeB = 0;
    else
      event.routeA = state_.routeBits;
  } else {
    if (direction)
      event.routeA = 0;
    else
      event.routeB = state_.routeBits;
  }
}
bool ExternalConnection::handleInternal(const Event &event) {
  if (state_.handle &&
      state_.handle(state_.handlerContext, nullptr, event) == 2)
    return true;
  return Connection::handleInternal(event);
}
int ExternalConnection::getType() const { return 2; }
void ExternalConnection::getAddress(const char *&address,
                                    unsigned short &port) const {
  address = "(External)";
  port = 0;
}
} // namespace Presonus::UC
