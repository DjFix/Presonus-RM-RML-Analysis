#include "presonus/uc/midi_endpoint_registry.hpp"

namespace Presonus::UC {
MidiEndpointRegistry::MidiEndpointRegistry()
    : senderIds_(100, 128), local_(0, 5), remote_(0, 5), listeners_(0, 5) {}

MidiEndpointRegistry::~MidiEndpointRegistry() = default;

bool MidiEndpointRegistry::hasListeners() const {
  return listeners_.count() != 0;
}

void MidiEndpointRegistry::removeListener(IMidiNetworkListener *listener) {
  listeners_.remove(listener);
}
} // namespace Presonus::UC
