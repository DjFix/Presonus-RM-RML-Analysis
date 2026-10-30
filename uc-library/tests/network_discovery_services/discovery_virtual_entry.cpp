#include "presonus/uc/udp_discovery.hpp"
#include <cstdlib>
void discoveryControls(Presonus::UC::UDPDiscoveryHandler &handler,
                       Presonus::UC::IDiscoveryReplyHandler *reply) {
  handler.setReplyHandler(reply);
  if (!handler.startBrowsing())
    std::abort();
  handler.stopBrowsing();
}
void discoveryUpdate(Presonus::UC::UDPDiscoveryHandler &handler, void *entry,
                     const char *name) {
  handler.updateServer(entry, name);
}
