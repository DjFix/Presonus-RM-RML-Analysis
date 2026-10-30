#pragma once
#include "presonus/uc/udp_discovery.hpp"
namespace presonus::uc {
struct DiscoveryOwnedEntry;
// Independent source-port ownership, never an original entry layout/lifecycle.
// Entry views stay stable; registry lifetime must outlive all borrowed views.
class DiscoveryEntryOwnership {
public:
  DiscoveryEntryOwnership() = default;
  ~DiscoveryEntryOwnership();
  DiscoveryEntryOwnership(const DiscoveryEntryOwnership &) = delete;
  DiscoveryEntryOwnership &operator=(const DiscoveryEntryOwnership &) = delete;
  Presonus::UC::UDPDiscoveryEntry *create();
  DiscoveryEntryState &stateFor(Presonus::UC::UDPDiscoveryEntry *);
  void destroy(Presonus::UC::UDPDiscoveryEntry *);
  int count() const { return owners_.count(); }

private:
  Core::Vector<DiscoveryOwnedEntry *> owners_;
};
} // namespace presonus::uc
