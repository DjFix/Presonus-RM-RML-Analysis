#include "presonus/avb/protocol.hpp"
#include "presonus/avb/receive_services.hpp"

#include <cstdint>

namespace Presonus::AVB {
AvbListener *AvbManagerBase::findListener(unsigned char identifier) {
  return receiveContext_->listeners.findIf([identifier](AvbListener *stream) {
    return stream->inspectState().identifierByte == identifier;
  });
}

AvbTalker *AvbManagerBase::findTalker(unsigned char identifier) {
  return receiveContext_->talkers.findIf([identifier](AvbTalker *stream) {
    return stream->inspectState().identifierByte == identifier;
  });
}

unsigned char AvbManagerBase::lookupNextTalkerIndex() {
  std::uint32_t result = 0;
  for (auto *stream : receiveContext_->talkers)
    result = (result +
              static_cast<std::uint32_t>(stream->inspectState().integerWord)) &
             255U;
  return static_cast<unsigned char>(result);
}
} // namespace Presonus::AVB
