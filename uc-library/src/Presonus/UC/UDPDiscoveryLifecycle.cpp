#include "presonus/uc/discovery_ownership.hpp"
#include "presonus/uc/multicast_connection.hpp"
#include "presonus/uc/no_member_events.hpp"
#include <algorithm>
#include <cstring>
#include <new>
#include <stdexcept>
namespace presonus::uc {
struct DiscoveryOwnedEntry {
  DiscoveryEntryState state;
  Presonus::UC::UDPDiscoveryEntry view;
  DiscoveryOwnedEntry() : view(DiscoverySourcePortTag{}, state) {}
};
DiscoveryEntryOwnership::~DiscoveryEntryOwnership() {
  for (int index = 0; index < owners_.count(); ++index)
    delete owners_.at(index);
}
Presonus::UC::UDPDiscoveryEntry *DiscoveryEntryOwnership::create() {
  auto *owner = new DiscoveryOwnedEntry;
  if (!owners_.add(owner)) {
    delete owner;
    throw std::bad_alloc();
  }
  return &owner->view;
}
DiscoveryEntryState &
DiscoveryEntryOwnership::stateFor(Presonus::UC::UDPDiscoveryEntry *view) {
  for (int index = 0; index < owners_.count(); ++index)
    if (&owners_.at(index)->view == view)
      return owners_.at(index)->state;
  throw std::invalid_argument(
      "Entry is not owned by this source-port registry");
}
void DiscoveryEntryOwnership::destroy(Presonus::UC::UDPDiscoveryEntry *view) {
  for (int index = 0; index < owners_.count(); ++index) {
    auto *owner = owners_.at(index);
    if (&owner->view == view) {
      owners_.removeAt(index);
      delete owner;
      return;
    }
  }
  // Detect a violated source-port ownership precondition; never silently fake
  // deletion of a borrowed view. This path is outside the original test domain.
  throw std::invalid_argument("Cannot delete a borrowed or expired entry view");
}
} // namespace presonus::uc
namespace Presonus::UC {
bool UDPDiscoveryEntry::updateHostName(const char *name) {
  if (!name)
    name = "";
  if (state_.displayName.compare(name, true) == 0)
    return false;
  const auto count = std::min<std::size_t>(std::strlen(name), 63);
  // App adaptation atop genuine CCL storage preserves no-clear/interior alias
  // behavior without undefined native overlapping strncpy.
  std::memmove(state_.displayName.getBuffer(), name, count);
  state_.displayName.getBuffer()[count] = 0;
  return true;
}
bool UDPDiscoveryHandler::startup(bool) {
  state_.connection->addReceiver(static_cast<IMulticastReceiver *>(this));
  return true;
}
void UDPDiscoveryHandler::shutdown() {
  state_.connection->removeReceiver(static_cast<IMulticastReceiver *>(this));
  for (int index = 0; index < state_.entries.count(); ++index)
    state_.ownership->destroy(state_.entries.at(index));
  state_.entries.resize(0);
}
void UDPDiscoveryHandler::removeServer(UDPDiscoveryEntry *entry) {
  state_.reply->onServerRemoved(entry);
  state_.entries.remove(entry);
  state_.ownership->destroy(entry);
}
void UDPDiscoveryHandler::restartBrowsing() {
  Core::Vector<UDPDiscoveryEntry *> remote;
  for (int index = 0; index < state_.entries.count(); ++index) {
    auto *entry = state_.entries.at(index);
    if (!entry->state_.flag0)
      remote.add(entry);
  }
  for (int index = 0; index < remote.count(); ++index)
    removeServer(remote.at(index));
  state_.counter28 = 0;
  state_.counter2c = 0;
}
void UDPDiscoveryHandler::unregisterServer(void *identity) {
  auto *entry = static_cast<UDPDiscoveryEntry *>(identity);
  if (!entry->state_.flag3 && !entry->state_.flag4) {
    DiscoveryLeaveEvent leave;
    leave.header.type = 17484;
    leave.header.reserved04 = 16;
    leave.header.routeA = static_cast<std::uint32_t>(entry->state_.identifier);
    leave.header.routeB = 0;
    state_.connection->sendEvent(leave.header);
  }
  state_.entries.remove(entry);
  state_.ownership->destroy(entry);
}
} // namespace Presonus::UC
