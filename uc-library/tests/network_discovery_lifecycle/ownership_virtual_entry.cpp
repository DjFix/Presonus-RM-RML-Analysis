#include "presonus/uc/discovery_handler.hpp"
bool ownershipStartup(Presonus::UC::IDiscoveryHandler &handler, bool flag) {
  return handler.startup(flag);
}
void ownershipRestart(Presonus::UC::IDiscoveryHandler &handler) {
  handler.restartBrowsing();
}
void ownershipShutdown(Presonus::UC::IDiscoveryHandler &handler) {
  handler.shutdown();
}
void ownershipUnregister(Presonus::UC::IDiscoveryHandler &handler,
                         void *entry) {
  handler.unregisterServer(entry);
}
