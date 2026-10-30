#include "core/system/coretime.h"
#include "presonus/uc/client_implementation.hpp"
namespace presonus::uc {
std::uint64_t clientSystemMilliseconds() {
  return static_cast<std::uint64_t>(Core::SystemClock::getMilliseconds());
}
} // namespace presonus::uc
namespace Presonus::UC {
namespace {
constexpr auto signKey = std::uint64_t{1} << 63;
bool signedLess(std::uint64_t a, std::uint64_t b) {
  return (a ^ signKey) < (b ^ signKey);
}
} // namespace
ClientImplementation::ClientImplementation(presonus::uc::ClientStatePortTag,
                                           INetworkManager &manager,
                                           std::uint32_t routeA,
                                           std::uint32_t routeB)
    : manager_(manager), routeA_(routeA), routeB_(routeB) {}
bool ClientImplementation::hasParamChanged(void *context, int timeout) const {
  const auto now = getSystemTime();
  const auto limit =
      static_cast<std::uint64_t>(static_cast<std::int64_t>(timeout));
  for (int i = 0; i < changes_.count(); ++i) {
    const auto &change = changes_.at(i);
    if (change.context == context && signedLess(now - change.timeBits, limit))
      return true;
  }
  return false;
}
void ClientImplementation::resetParamChanges() { changes_.setCount(0); }
void ClientImplementation::resetParamChanges(void *context) {
  for (;;) {
    int found = -1;
    for (int i = 0; i < changes_.count(); ++i)
      if (changes_.at(i).context == context) {
        found = i;
        break;
      }
    if (found < 0)
      return;
    changes_.removeAt(found);
  }
}
void ClientImplementation::setLastParamChange(void *context) {
  const auto now = getSystemTime();
  for (int i = 0; i < changes_.count(); ++i)
    if (changes_.at(i).context == context) {
      changes_.removeAt(i);
      break;
    }
  while (changes_.count() > 63)
    changes_.removeAt(0);
  const auto count = changes_.count();
  // Actual public container storage/count APIs: preserve the unused second word
  // and stale cells. No access to private Core layout or invented Core class.
  auto &item = changes_.getItems()[count];
  item.context = context;
  item.timeBits = now;
  changes_.setCount(count + 1);
}
void ClientImplementation::markAlive() { lastAlive_ = getSystemTime(); }
int ClientImplementation::sendEvent(Event &event) {
  event.routeA = routeA_;
  event.routeB = routeB_;
  return manager_.sendEvent(event, 0);
}
void ClientImplementation::keepAlive() {
  const auto now = getSystemTime();
  if (!signedLess(1499, now - lastAlive_))
    return;
  Event event{0x4b41, 16, 0, 0};
  sendEvent(event);
  lastAlive_ = now;
}
// Original body has no calls or observable writes. The payload type remains
// forward-declared; no guessed original payload fields/layout are required.
void ClientImplementation::receiveEvent(const LoopbackReplyEvent &) {}
} // namespace Presonus::UC
