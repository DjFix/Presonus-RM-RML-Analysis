#include "presonus/uc/udp_discovery.hpp"
#include <algorithm>
#include <cstring>
namespace Presonus::UC {
void UDPDiscoveryHandler::setConnection(MulticastConnection *connection) {
  state_.connection = connection;
}
void UDPDiscoveryHandler::setReplyHandler(IDiscoveryReplyHandler *reply) {
  state_.reply = reply;
}
bool UDPDiscoveryHandler::startBrowsing() {
  state_.browsing = 1;
  return true;
}
void UDPDiscoveryHandler::stopBrowsing() { state_.browsing = 0; }
UDPDiscoveryEntry *UDPDiscoveryHandler::find(const char *host,
                                             unsigned short port,
                                             int identifier) const {
  for (int index = 0; index < state_.entries.count(); ++index) {
    auto *entry = state_.entries.at(index);
    const auto &value = entry->state_;
    if (value.flag0 == 0 && value.port == port &&
        value.identifier == identifier &&
        value.host.compare(host ? host : "", true) == 0)
      return entry;
  }
  return nullptr;
}
UDPDiscoveryEntry *UDPDiscoveryHandler::findLocal(int identifier) const {
  for (int index = 0; index < state_.entries.count(); ++index) {
    auto *entry = state_.entries.at(index);
    const auto &value = entry->state_;
    if (value.flag3 == 0 && value.flag0 != 0 && value.identifier == identifier)
      return entry;
  }
  return nullptr;
}
void UDPDiscoveryHandler::updateServer(void *identity, const char *name) {
  auto &entry = static_cast<UDPDiscoveryEntry *>(identity)->state_;
  if (name)
    static_cast<UDPDiscoveryEntry *>(identity)->updateHostName(name);
  const auto version = ((entry.versionWord >> 16) & 255U) + 1U;
  entry.versionWord =
      (entry.versionWord & ~0xff0000U) | ((version % 255U) << 16);
  entry.dirty = 1;
  state_.counter28 = 0;
  state_.counter2c = 0;
}
} // namespace Presonus::UC
