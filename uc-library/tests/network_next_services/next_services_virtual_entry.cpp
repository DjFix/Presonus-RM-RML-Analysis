#include "presonus/uc/network_manager_services.hpp"

[[gnu::noinline]] int
invokeReporter(Presonus::UC::INetworkManager &manager, bool remove,
               Presonus::UC::INetworkErrorReporter *reporter) {
  return remove ? manager.removeErrorReporter(reporter)
                : manager.addErrorReporter(reporter);
}
