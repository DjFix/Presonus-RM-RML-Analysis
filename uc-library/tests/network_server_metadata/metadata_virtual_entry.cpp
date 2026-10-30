#include "presonus/uc/server.hpp"

int metadataTypeViaInterface(const Presonus::UC::Server &server) {
  return server.getType();
}
